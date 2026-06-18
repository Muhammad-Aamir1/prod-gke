import os, json, asyncio, httpx, logging, difflib, shlex
from tools import get_tool_defs, call_tool, set_role, get_role

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "openrouter/free")
OPENROUTER_FALLBACK_MODELS = (os.environ.get("OPENROUTER_FALLBACK_MODELS", "openrouter/auto")).split(",")
OPENROUTER_MAX_TOKENS = int(os.environ.get("OPENROUTER_MAX_TOKENS", "2000"))
SITE_URL = os.environ.get("SITE_URL", "http://localhost:8080")
SITE_NAME = "prod-gke AI Agent"
MAX_HISTORY = int(os.environ.get("MAX_HISTORY", "20"))

_logger = logging.getLogger("agent")

def make_system_prompt(role: str = "admin") -> str:
    return f"""You are a DevOps AI agent managing a production GKE cluster called prod-gke. You have full access to kubectl, helm, gcloud, and can make HTTP requests.

## Current Role: {role}
Your kubectl commands run with the role selected by the user. Respect your role's limitations:
- viewer: read-only access to cluster resources (can view but not create/update/delete)
- edit: can modify resources but not RBAC
- admin: full cluster-admin access and shell access (pipelines, chaining commands allowed)
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
- Always confirm before making destructive changes. Ask the user "I can [action], shall I proceed?" and wait for explicit yes before calling destructive tools
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

_KNOWN_WORDS = {
    "kubectl", "helm", "gcloud", "argocd", "prometheus", "grafana", "kubernetes",
    "deployment", "service", "pod", "namespace", "configmap", "secret", "ingress",
    "statefulset", "daemonset", "replicaset", "pv", "pvc", "storageclass",
    "cluster", "node", "proxy", "rollout", "restart", "scale", "logs", "describe",
    "create", "apply", "delete", "edit", "get", "list", "watch", "exec",
    "frontend", "backend", "postgres", "redis", "monitoring", "prod-ns",
    "loadbalancer", "clusterip", "nodeport", "rollback", "health", "status",
    "deploy", "upgrade", "install", "uninstall", "rollback", "release",
    "pods", "services", "deployments", "namespaces", "configmaps", "secrets",
    "ingresses", "statefulsets", "daemonsets", "replicasets", "persistentvolumes",
    "persistentvolumeclaims", "storageclasses", "nodes", "clusters",
    "kubectl", "helm", "gcloud", "argocd", "prometheus", "grafana",
    "application", "applicationset", "sync", "healthy", "degraded", "outofsync",
}

def _suggest_spelling_fix(text: str) -> tuple[str, list[str]]:
    tokens = shlex.split(text) if shlex.split(text) else text.split()
    corrections = []
    fixed_tokens = []
    for t in tokens:
        t_lower = t.lower()
        if t_lower not in _KNOWN_WORDS and len(t) > 2:
            matches = difflib.get_close_matches(t_lower, _KNOWN_WORDS, n=1, cutoff=0.7)
            if matches:
                suggestion = matches[0]
                if t_lower != suggestion:
                    corrections.append(f"\"{t}\" -> \"{suggestion}\"")
                    fixed_tokens.append(suggestion if t[0].islower() else suggestion.capitalize())
                    continue
        fixed_tokens.append(t)
    return " ".join(fixed_tokens), corrections

def _correct_spelling(messages: list) -> list:
    corrected = []
    for msg in messages:
        if msg.get("role") == "user" and msg.get("content"):
            fixed, corrections = _suggest_spelling_fix(msg["content"])
            if corrections:
                _logger.info("spelling_corrections", extra={"corrections": corrections})
                fixed_msg = dict(msg)
                fixed_msg["content"] = fixed
                fixed_msg["_original"] = msg["content"]
                fixed_msg["_corrections"] = corrections
                corrected.append(fixed_msg)
                continue
        corrected.append(msg)
    return corrected

class Agent:
    def __init__(self):
        self.tool_defs = get_tool_defs()
        self._models = [m.strip() for m in [OPENROUTER_MODEL] + OPENROUTER_FALLBACK_MODELS if m.strip()]

    async def run(self, messages: list, role: str = "admin") -> dict:
        set_role(role)
        corrected = _correct_spelling(messages)
        corrections = []
        for m in corrected:
            corr = m.pop("_corrections", None) if isinstance(m, dict) else None
            if corr:
                corrections.extend(corr)
        system_msg = {"role": "system", "content": make_system_prompt(role)}
        all_messages = [system_msg] + corrected

        for loop_attempt in range(3):
            response_text, tool_calls, assistant_msg = await self._llm_call(all_messages)

            if not tool_calls:
                text = response_text
                if corrections:
                    text = "Note: assuming you meant " + ", ".join(corrections) + "\n\n" + text
                if text and not text.startswith("Error:"):
                    return {
                        "response": text,
                        "messages": messages + [{"role": "assistant", "content": text}],
                        "extra": {"spelling_corrections": corrections} if corrections else {}
                    }
                if loop_attempt < 2:
                    _logger.warning("retry_empty_response", extra={"attempt": loop_attempt + 1})
                    continue
                return {
                    "response": text or "I encountered an issue processing your request. Please try again.",
                    "messages": messages + [{"role": "assistant", "content": text or ""}],
                    "extra": {"spelling_corrections": corrections} if corrections else {}
                }

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
                    "content": result[:4000] if len(result) > 4000 else result
                })

            final_text, final_tools, _ = await self._llm_call(all_messages, allow_tools=True)

            if final_tools:
                all_messages.append({"role": "assistant", "content": final_text or ""})
                for tc in final_tools:
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
                        "content": result[:4000] if len(result) > 4000 else result
                    })
                final_text, _, _ = await self._llm_call(all_messages, allow_tools=False)

            text = final_text or "Done. Review the results above."
            if corrections:
                text = "Note: assuming you meant " + ", ".join(corrections) + "\n\n" + text
                extra["spelling_corrections"] = corrections
            return {
                "response": text,
                "messages": messages + [{"role": "assistant", "content": text}],
                "extra": extra
            }

        return {
            "response": "Retried multiple times but could not process. Please rephrase.",
            "messages": messages,
            "extra": {}
        }

    async def run_stream(self, messages: list, role: str = "admin"):
        set_role(role)
        corrected = _correct_spelling(messages)
        corrections = []
        for m in corrected:
            corr = m.pop("_corrections", None) if isinstance(m, dict) else None
            if corr:
                corrections.extend(corr)
        system_msg = {"role": "system", "content": make_system_prompt(role)}
        all_messages = [system_msg] + corrected

        for loop_attempt in range(3):
            yield {"type": "thinking"}
            response_text, tool_calls, assistant_msg = await self._llm_call(all_messages)

            if not tool_calls:
                text = response_text
                if corrections:
                    text = "Note: assuming you meant " + ", ".join(corrections) + "\n\n" + text
                if text and not text.startswith("Error:"):
                    yield {"type": "done", "response": text, "messages": messages + [{"role": "assistant", "content": text}], "extra": {"spelling_corrections": corrections} if corrections else {}}
                    return
                if loop_attempt < 2:
                    yield {"type": "retry", "reason": "empty"}
                    continue
                yield {"type": "done", "response": text or "I encountered an issue processing your request. Please try again.", "messages": messages + [{"role": "assistant", "content": text or ""}], "extra": {"spelling_corrections": corrections} if corrections else {}}
                return

            all_messages.append(assistant_msg)
            extra = {"tool_calls": []}

            for tc in tool_calls:
                set_role(role)
                name = tc.get("name")
                call_id = tc.get("id", name)
                args = tc.get("arguments", {})
                yield {"type": "tool_call", "name": name, "args": args}
                result = await call_tool(name, args)
                truncated = result[:2000] if len(result) > 2000 else result
                extra["tool_calls"].append({"name": name, "args": args, "result": truncated})
                yield {"type": "tool_result", "name": name, "result": truncated}
                all_messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": result[:4000] if len(result) > 4000 else result
                })

            yield {"type": "thinking"}
            final_text, final_tools, _ = await self._llm_call(all_messages, allow_tools=True)

            if final_tools:
                all_messages.append({"role": "assistant", "content": final_text or ""})
                for tc in final_tools:
                    set_role(role)
                    name = tc.get("name")
                    call_id = tc.get("id", name)
                    args = tc.get("arguments", {})
                    yield {"type": "tool_call", "name": name, "args": args}
                    result = await call_tool(name, args)
                    truncated = result[:2000] if len(result) > 2000 else result
                    extra["tool_calls"].append({"name": name, "args": args, "result": truncated})
                    yield {"type": "tool_result", "name": name, "result": truncated}
                    all_messages.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": result[:4000] if len(result) > 4000 else result
                    })
                yield {"type": "thinking"}
                final_text, _, _ = await self._llm_call(all_messages, allow_tools=False)

            text = final_text or "Done. Review the results above."
            if corrections:
                text = "Note: assuming you meant " + ", ".join(corrections) + "\n\n" + text
                extra["spelling_corrections"] = corrections
            yield {"type": "done", "response": text, "messages": messages + [{"role": "assistant", "content": text}], "extra": extra}
            return

        yield {"type": "done", "response": "Retried multiple times but could not process. Please rephrase.", "messages": messages, "extra": {}}

    async def _llm_call(self, messages: list, allow_tools: bool = True) -> tuple:
        if not OPENROUTER_API_KEY:
            return "Error: OPENROUTER_API_KEY not configured.", [], {}

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": SITE_URL,
            "X-Title": SITE_NAME,
        }

        models_to_try = list(self._models)
        last_error = ""

        for model in models_to_try:
            payload = {
                "model": model,
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
                    last_error = str(e)
                    if attempt < 2:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    break

                if "error" in data:
                    err = data["error"]
                    code = err.get("code", 0)
                    msg_text = err.get("message", str(err))
                    last_error = f"{resp.status_code}: {msg_text}"
                    if code == 429 and attempt < 2:
                        retry_after = err.get("metadata", {}).get("retry_after_seconds", 5)
                        await asyncio.sleep(retry_after + 1)
                        continue
                    _logger.warning("llm_error", extra={
                        "model": model, "status": resp.status_code,
                        "error": msg_text[:200], "attempt": attempt + 1
                    })
                    break

                choice = data.get("choices", [{}])[0]
                msg = choice.get("message", {})
                content = msg.get("content") or ""
                finish_reason = choice.get("finish_reason", "")
                tool_calls_raw = msg.get("tool_calls", [])

                if not content and not tool_calls_raw and finish_reason != "tool_calls":
                    last_error = f"empty_response (finish_reason={finish_reason})"
                    if attempt < 2:
                        await asyncio.sleep(1)
                        continue
                    _logger.warning("llm_empty_response", extra={
                        "model": model, "finish_reason": finish_reason
                    })
                    return "", [], {}

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

            _logger.info("model_failed", extra={
                "model": model, "error": last_error, "falling_back": bool(models_to_try)
            })

        err_msg = f"All models failed. Last error: {last_error}"
        _logger.error("all_models_failed", extra={"error": last_error})
        return f"Error: {err_msg}", [], {}
