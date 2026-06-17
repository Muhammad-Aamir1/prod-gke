import subprocess, json, os, asyncio, httpx
from typing import Any

TOOLS = []

def tool(name, desc, params):
    def dec(fn):
        fn._tool = {"name": name, "description": desc, "parameters": params, "fn": fn}
        TOOLS.append(fn._tool)
        return fn
    return dec

def _run(cmd: str, timeout=30) -> str:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        out = r.stdout.strip()
        err = r.stderr.strip()
        if r.returncode != 0:
            return f"Error: {err or out}"
        return out or "(empty output)"
    except subprocess.TimeoutExpired:
        return "Error: command timed out"
    except Exception as e:
        return f"Error: {e}"

@tool("run_kubectl", "Run any kubectl command against the GKE cluster", {
    "type": "object", "properties": {
        "command": {"type": "string", "description": "kubectl command (e.g. 'get pods -n prod-ns')"}
    }, "required": ["command"]
})
async def run_kubectl(command: str) -> str:
    return _run(f"kubectl {command}", timeout=30)

@tool("run_helm", "Run any helm command", {
    "type": "object", "properties": {
        "command": {"type": "string", "description": "helm command (e.g. 'list -n monitoring')"}
    }, "required": ["command"]
})
async def run_helm(command: str) -> str:
    return _run(f"helm {command}", timeout=30)

@tool("run_gcloud", "Run any gcloud command", {
    "type": "object", "properties": {
        "command": {"type": "string", "description": "gcloud command"}
    }, "required": ["command"]
})
async def run_gcloud(command: str) -> str:
    return _run(f"gcloud {command}", timeout=30)

@tool("cluster_health", "Check overall cluster health: pods, nodes, services", {
    "type": "object", "properties": {}
})
async def cluster_health(**kw) -> str:
    pods = _run("kubectl get pods -A --no-headers 2>&1 | awk '{print $2, $3}' | sort | uniq -c | sort -rn", timeout=15)
    nodes = _run("kubectl get nodes --no-headers -o wide", timeout=10)
    services = _run("kubectl get svc -A --no-headers | grep -E 'LoadBalancer|NodePort' | awk '{print $2, $4, $5}'", timeout=10)
    pvcs = _run("kubectl get pvc -A --no-headers", timeout=10)
    return f"=== Pods ===\n{pods}\n\n=== Nodes ===\n{nodes}\n\n=== LoadBalancer Services ===\n{services}\n\n=== PVCs ===\n{pvcs}"

@tool("make_request", "Make HTTP request to a service URL", {
    "type": "object", "properties": {
        "url": {"type": "string", "description": "Full URL to request"},
        "method": {"type": "string", "description": "HTTP method", "default": "GET"}
    }, "required": ["url"]
})
async def make_request(url: str, method: str = "GET") -> str:
    try:
        async with httpx.AsyncClient(timeout=15, verify=False) as c:
            r = await c.request(method, url)
            return f"Status: {r.status_code}\nBody:\n{r.text[:2000]}"
    except Exception as e:
        return f"Error: {e}"

@tool("deploy_kustomize", "Deploy applications using kustomize from a path", {
    "type": "object", "properties": {
        "path": {"type": "string", "description": "Path to kustomization directory (e.g. '03-k8s-manifests/overlays/dev')"}
    }, "required": ["path"]
})
async def deploy_kustomize(path: str) -> str:
    return _run(f"kubectl apply -k {path}", timeout=60)

@tool("deploy_helm", "Deploy or upgrade a Helm chart from a directory", {
    "type": "object", "properties": {
        "name": {"type": "string", "description": "Helm release name"},
        "path": {"type": "string", "description": "Path to chart directory"},
        "namespace": {"type": "string", "description": "Namespace to deploy into"},
        "values": {"type": "string", "description": "Optional values file path"}
    }, "required": ["name", "path", "namespace"]
})
async def deploy_helm(name: str, path: str, namespace: str, values: str = "") -> str:
    cmd = f"helm upgrade --install {name} {path} -n {namespace} --create-namespace"
    if values:
        cmd += f" -f {values}"
    return _run(cmd, timeout=120)

@tool("query_prometheus", "Query Prometheus for a metric", {
    "type": "object", "properties": {
        "query": {"type": "string", "description": "PromQL query (e.g. 'rate(process_cpu_seconds_total[1m])')"}
    }, "required": ["query"]
})
async def query_prometheus(query: str) -> str:
    result = _run(f'kubectl exec -n monitoring deployment/monitoring-kube-prometheus-prometheus -- wget -qO- "http://localhost:9090/api/v1/query?query={query}"', timeout=15)
    try:
        data = json.loads(result)
        results = data.get("data", {}).get("result", [])
        if not results:
            return "No data for query"
        lines = []
        for r in results[:20]:
            m = r.get("metric", {})
            v = r.get("value", [None, ""])[1]
            labels = ",".join(f"{k}={v}" for k, v in m.items() if k != "__name__")
            lines.append(f"[{v}] {labels}")
        return "\n".join(lines) if lines else "No results"
    except json.JSONDecodeError:
        return f"Raw: {result[:1000]}"

@tool("read_logs", "Read logs from pods matching a label", {
    "type": "object", "properties": {
        "label": {"type": "string", "description": "Label selector (e.g. 'app=backend')"},
        "namespace": {"type": "string", "description": "Namespace"},
        "tail": {"type": "integer", "description": "Number of lines", "default": 20}
    }, "required": ["label", "namespace"]
})
async def read_logs(label: str, namespace: str = "prod-ns", tail: int = 20) -> str:
    return _run(f"kubectl logs -n {namespace} -l {label} --tail={tail}", timeout=15)

@tool("restart_deployment", "Restart pods in a deployment", {
    "type": "object", "properties": {
        "name": {"type": "string", "description": "Deployment name"},
        "namespace": {"type": "string", "description": "Namespace"}
    }, "required": ["name", "namespace"]
})
async def restart_deployment(name: str, namespace: str) -> str:
    return _run(f"kubectl rollout restart deployment/{name} -n {namespace}", timeout=30)

def get_tool_defs():
    return [{
        "type": "function",
        "function": {
            "name": t["name"],
            "description": t["description"],
            "parameters": t["parameters"]
        }
    } for t in TOOLS]

async def call_tool(name: str, args: dict) -> str:
    for t in TOOLS:
        if t["name"] == name:
            fn = t["fn"]
            if asyncio.iscoroutinefunction(fn):
                return await fn(**args)
            return fn(**args)
    return f"Error: unknown tool '{name}'"
