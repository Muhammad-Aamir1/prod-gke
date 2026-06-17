import os, json, asyncio, httpx, logging
from tools import get_tool_defs, call_tool, set_role, get_role

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "openrouter/free")
OPENROUTER_MAX_TOKENS = int(os.environ.get("OPENROUTER_MAX_TOKENS", "2000"))
SITE_URL = os.environ.get("SITE_URL", "http://localhost:8080")
SITE_NAME = "prod-gke AI Agent"
MAX_HISTORY = int(os.environ.get("MAX_HISTORY", "20"))

def make_system_prompt(role: str = "admin") -> str:
    return f"""You are a DevOps AI agent managing a production GKE cluster called prod-gke. You have full access to kubectl, helm, gcloud, and can make HTTP requests.

## Current Role: {role}
Your kubectl commands run with the role selected by the user. Respect your role's limitations:
- viewer: read-only access to cluster resources (can view but not create/update/delete)
- edit: can modify resources but not RBAC
- admin: full cluster-admin access
If a command fails due to permissions, inform the user and suggest a higher role.

## Cluster Overview
- **Cluster**: dev-cluster in us-central1, GKE 1.35.5, Dataplane V2
- **Prod Namespace**: prod-ns (applications: backend API, frontend web, postgres, redis)
- **Monitoring Namespace**: monitoring (kube-prometheus-stack: Prometheus, Grafana, Alertmanager)
- **ArgoCD Namespace**: argocd (GitOps operator)
- **External Secrets**: external-secrets (syncs GCP secrets)

## Applications
- **Frontend**: Express.js, 3 replicas, LoadBalancer at frontend-svc
- **Backend**: Express.js with PostgreSQL + Redis, 2 replicas
- **Postgres**: StatefulSet with 10Gi PVC
- **Redis**: Deployment with AOF persistence

## Your Capabilities
You have these tools available. Use them to fulfill user requests:
1. **run_kubectl** - Run any kubectl command
2. **run_helm** - Run helm commands  
3. **run_gcloud** - Run gcloud commands
4. **cluster_health** - Get comprehensive cluster health
5. **make_request** - Make HTTP requests to services
6. **deploy_kustomize** - Deploy Kustomize overlays
7. **deploy_helm** - Deploy Helm charts
8. **query_prometheus** - Query Prometheus metrics
9. **read_logs** - Read pod logs
10. **restart_deployment** - Restart deployments

## Instructions
- Always check cluster health first when troubleshooting
- Use Prometheus to verify monitoring is collecting metrics
- Deployments should be done through kubectl/helm, not by modifying files
- When deploying, verify the resources were created successfully
- For application issues, check logs first, then pod status, then events
- Keep responses concise but informative
- Always confirm before making destructive changes
- When the user asks about monitoring, check Prometheus and Grafana
- Call tools using the function calling API (the system will handle tool execution)
- After calling tools, summarize the results for the user in plain text
- You can call multiple tools in parallel if they are independent
- Always respond in plain text with no markdown formatting (no **bold**, no *italic*, no ```code blocks```, no bullet lists with - or *)
- Use simple plain text:
  - Use simple lines like: Pods: all running (5/5)
  - Use simple lines like: Services: frontend LoadBalancer at 34.171.99.210
  - Use simple lines like: Status: healthy
"""

class Agent:
    def __init__(self):
        self.tool_defs = get_tool_defs()

    async def run(self, messages: list, role: str = "admin") -> dict:
        set_role(role)
        system_msg = {"role": "system", "content": make_system_prompt(role)}
        all_messages = [system_msg] + messages

        response_text, tool_calls, assistant_msg = await self._llm_call(all_messages)

        if tool_calls:
            all_messages.append(assistant_msg)

            extra = {"tool_calls": []}
            for tc in tool_calls:
                set_role(role)
                name = tc.get("name")
                call_id = tc.get("id", name)
                args = tc.get("arguments", {})
                result = await call_tool(name, args)
                extra["tool_calls"].append({
                    "name": name,
                    "args": args,
                    "result": result[:2000] if len(result) > 2000 else result
                })
                all_messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": result[:3000] if len(result) > 3000 else result
                })

            final_text, _, _ = await self._llm_call(all_messages, allow_tools=False)
            text = final_text or "Command executed. Check the tool results above for details."
            return {
                "response": text,
                "messages": messages + [{"role": "assistant", "content": text}],
                "extra": extra
            }

        text = response_text or "No response from agent."
        return {
            "response": text,
            "messages": messages + [{"role": "assistant", "content": text}],
            "extra": {}
        }

    async def _llm_call(self, messages: list, allow_tools: bool = True) -> tuple:
        if not OPENROUTER_API_KEY:
            return "Error: OPENROUTER_API_KEY environment variable not set. Please set it and restart the agent.", [], {}

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": SITE_URL,
            "X-Title": SITE_NAME,
        }

        payload = {
            "model": OPENROUTER_MODEL,
            "messages": messages,
            "max_tokens": OPENROUTER_MAX_TOKENS,
        }
        if allow_tools:
            payload["tools"] = self.tool_defs
            payload["tool_choice"] = "auto"

        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=90) as client:
                    resp = await client.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    data = resp.json()
            except Exception as e:
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return f"Error calling OpenRouter: {e}", [], {}

            if "error" in data:
                err = data["error"]
                code = err.get("code", 0)
                if code == 429 and attempt < 2:
                    retry_after = err.get("metadata", {}).get("retry_after_seconds", 5)
                    await asyncio.sleep(retry_after + 1)
                    continue
                logging.error(f"OpenRouter error: status={resp.status_code}, detail={json.dumps(err)[:500]}, request_messages={len(messages)}")
                return f"OpenRouter error ({resp.status_code}): {err.get('message', str(err))}", [], {}

            break

        choice = data.get("choices", [{}])[0]
        msg = choice.get("message", {})
        content = msg.get("content") or ""
        tool_calls_raw = msg.get("tool_calls", [])

        tool_calls = []
        for tc in tool_calls_raw:
            fn = tc.get("function", {})
            args_raw = fn.get("arguments", "{}")
            try:
                args = json.loads(args_raw)
            except json.JSONDecodeError:
                args = {"raw_args": args_raw}
            tool_calls.append({
                "id": tc.get("id", ""),
                "name": fn.get("name", "unknown"),
                "arguments": args,
            })

        return content, tool_calls, msg
