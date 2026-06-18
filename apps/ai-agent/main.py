from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
import os, json, time, logging, asyncio
from collections import defaultdict
from datetime import datetime, timezone

from agent import Agent, OPENROUTER_API_KEY
from tools import ROLE_TOKENS, _kubectl

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S%z',
)
_logger = logging.getLogger("main")

MAX_SESSIONS = int(os.environ.get("MAX_SESSIONS", "100"))
MAX_HISTORY = int(os.environ.get("MAX_HISTORY", "20"))
RATE_LIMIT_PER_SESSION = int(os.environ.get("RATE_LIMIT_PER_SESSION", "10"))
RATE_LIMIT_WINDOW = int(os.environ.get("RATE_LIMIT_WINDOW", "60"))
REDIS_URL = os.environ.get("REDIS_URL", "")

app = FastAPI(title="prod-gke AI Agent")
agent = Agent()

sessions = {}
_rate_buckets = defaultdict(list)

_redis = None
if REDIS_URL:
    try:
        import redis.asyncio as aioredis
        _redis = aioredis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=3, socket_timeout=3)
        _logger.info("redis_connected", extra={"url": REDIS_URL})
    except Exception as e:
        _logger.warning("redis_connect_failed", extra={"error": str(e), "fallback": "in-memory"})

def _check_rate_limit(session_id: str) -> bool:
    now = time.monotonic()
    bucket = _rate_buckets[session_id]
    cutoff = now - RATE_LIMIT_WINDOW
    while bucket and bucket[0] < cutoff:
        bucket.pop(0)
    if len(bucket) >= RATE_LIMIT_PER_SESSION:
        return False
    bucket.append(now)
    return True

async def _load_session(session_id: str) -> dict | None:
    if _redis:
        try:
            raw = await _redis.get(f"session:{session_id}")
            if raw:
                return json.loads(raw)
        except:
            pass
    return sessions.get(session_id)

async def _save_session(session_id: str, data: dict):
    data["_updated"] = datetime.now(timezone.utc).isoformat()
    if _redis:
        try:
            await _redis.setex(f"session:{session_id}", 86400, json.dumps(data))
        except:
            pass
    sessions[session_id] = data

def _rate_limit_headers(session_id: str) -> dict:
    bucket = _rate_buckets[session_id]
    remaining = max(0, RATE_LIMIT_PER_SESSION - len(bucket))
    return {
        "X-RateLimit-Limit": str(RATE_LIMIT_PER_SESSION),
        "X-RateLimit-Remaining": str(remaining),
        "X-RateLimit-Window": str(RATE_LIMIT_WINDOW),
    }

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>prod-gke AI Agent</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:#0d1117; color:#c9d1d9; height:100vh; display:flex; flex-direction:column; }
  .header { background:#161b22; border-bottom:1px solid #30363d; padding:16px 24px; display:flex; align-items:center; gap:12px; flex-wrap:wrap; }
  .header h1 { font-size:18px; font-weight:600; color:#f0f6fc; }
  .header span { font-size:12px; color:#8b949e; background:#21262d; padding:2px 8px; border-radius:10px; }
  .status { margin-left:auto; display:flex; align-items:center; gap:6px; font-size:13px; }
  .status-dot { width:8px; height:8px; border-radius:50%; background:#3fb950; }
  .status-dot.degraded { background:#d29922; }
  .status-dot.error { background:#f85149; }
  .chat { flex:1; overflow-y:auto; padding:20px 24px; display:flex; flex-direction:column; gap:12px; }
  .msg { max-width:85%; padding:12px 16px; border-radius:8px; line-height:1.5; font-size:14px; white-space:pre-wrap; }
  .user { background:#1f6feb; color:#fff; align-self:flex-end; }
  .bot { background:#21262d; color:#c9d1d9; align-self:flex-start; border:1px solid #30363d; }
  .bot.error { background:#3d1414; border-color:#f85149; }
  .tool-call { background:#161b22; border:1px solid #30363d; border-radius:6px; padding:10px 14px; margin:4px 0; font-size:13px; }
  .tool-call .name { color:#58a6ff; font-weight:500; }
  .tool-call .args { color:#8b949e; font-family:monospace; font-size:12px; margin-top:4px; white-space:pre-wrap; }
  .tool-call .result { color:#3fb950; font-family:monospace; font-size:12px; margin-top:4px; white-space:pre-wrap; max-height:200px; overflow-y:auto; }
  .tool-call .result.error { color:#f85149; }
  .input-row { border-top:1px solid #30363d; padding:12px 24px; background:#161b22; display:flex; gap:8px; }
  .input-row textarea { flex:1; background:#0d1117; border:1px solid #30363d; border-radius:6px; color:#c9d1d9; padding:10px 12px; font-size:14px; font-family:inherit; resize:none; min-height:44px; max-height:120px; }
  .input-row textarea:focus { outline:none; border-color:#1f6feb; }
  .input-row button { background:#238636; color:#fff; border:none; border-radius:6px; padding:10px 20px; font-size:14px; font-weight:500; cursor:pointer; }
  .input-row button:hover { background:#2ea043; }
  .input-row button:disabled { opacity:.5; cursor:not-allowed; }
  .loading { display:none; align-items:center; gap:8px; padding:8px 16px; color:#8b949e; font-size:13px; }
  .loading.active { display:flex; }
  .spinner { width:14px; height:14px; border:2px solid #30363d; border-top-color:#58a6ff; border-radius:50%; animation:spin .8s linear infinite; }
  @keyframes spin { to { transform:rotate(360deg); } }
  pre { background:#0d1117; border-radius:4px; padding:8px; overflow-x:auto; font-size:12px; margin:4px 0; }
  code { font-family:'SF Mono','Consolas',monospace; }
  .role-select { display:flex; align-items:center; gap:6px; font-size:12px; }
  .role-select select { background:#21262d; color:#c9d1d9; border:1px solid #30363d; border-radius:4px; padding:3px 6px; font-size:12px; cursor:pointer; outline:none; }
  .role-select select:focus { border-color:#1f6feb; }
  .role-badge { display:inline-block; padding:1px 6px; border-radius:3px; font-size:10px; font-weight:600; text-transform:uppercase; }
  .role-badge.viewer { background:#0d419d; color:#58a6ff; }
  .role-badge.edit { background:#096b3e; color:#3fb950; }
  .role-badge.admin { background:#a13026; color:#f85149; }
  .health-bar { display:flex; align-items:center; gap:6px; font-size:11px; color:#8b949e; }
  .health-bar .ok { color:#3fb950; }
  .health-bar .warn { color:#d29922; }
  .health-bar .bad { color:#f85149; }
</style>
</head>
<body>
<div class="header">
  <h1>prod-gke AI Agent</h1>
  <span>OpenRouter</span>
  <div class="role-select">
    <label>Role:</label>
    <select id="roleSelect">
      <option value="viewer">Viewer</option>
      <option value="edit">Edit</option>
      <option value="admin" selected>Admin</option>
    </select>
    <span class="role-badge admin" id="roleBadge">admin</span>
  </div>
  <div class="health-bar">
    <span class="ok" id="healthStatus">Cluster Connected</span>
  </div>
</div>
<div class="chat" id="chat"></div>
<div class="loading" id="loading"><div class="spinner"></div><span>Agent is thinking...</span></div>
<div class="input-row">
  <textarea id="input" placeholder="Tell the agent what to do..." rows="1"></textarea>
  <button id="sendBtn">Send</button>
</div>
<script>
  const chat = document.getElementById('chat');
  const input = document.getElementById('input');
  const loading = document.getElementById('loading');
  const sendBtn = document.getElementById('sendBtn');
  const roleSelect = document.getElementById('roleSelect');
  const roleBadge = document.getElementById('roleBadge');
  const healthStatus = document.getElementById('healthStatus');
  function genId() { try { return crypto.randomUUID(); } catch(e) { return Date.now().toString(36) + Math.random().toString(36).slice(2); } }
  let sessionId = localStorage.getItem('sessionId') || genId();
  localStorage.setItem('sessionId', sessionId);
  let currentRole = localStorage.getItem('agentRole') || 'admin';
  roleSelect.value = currentRole;
  updateRoleBadge(currentRole);

  function updateRoleBadge(role) {
    roleBadge.textContent = role;
    roleBadge.className = 'role-badge ' + role;
  }

  roleSelect.addEventListener('change', function() {
    currentRole = this.value;
    localStorage.setItem('agentRole', currentRole);
    updateRoleBadge(currentRole);
    addMsg('bot', '[Switched to ' + currentRole + ' role]');
  });

  function addMsg(type, content, extra) {
    const div = document.createElement('div');
    div.className = 'msg ' + type;
    if (extra) div.dataset.extra = JSON.stringify(extra);
    if (type === 'bot' && extra?.tool_calls) {
      let html = content;
      for (const tc of extra.tool_calls) {
        html += '<div class="tool-call"><div class="name">&#128295; ' + tc.name + '</div><div class="args">' + escapeHtml(JSON.stringify(tc.args, null, 2)) + '</div>';
        if (tc.result !== undefined) {
          const cls = tc.result.startsWith('Error') ? 'result error' : 'result';
          html += '<div class="' + cls + '">' + escapeHtml(tc.result.substring(0, 1000)) + '</div>';
        }
        html += '</div>';
      }
      div.innerHTML = html;
    } else {
      div.textContent = content;
    }
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
    return div;
  }

  async function typeMsg(div, text, speed) {
    speed = speed || 15;
    div.textContent = '';
    for (let i = 0; i < text.length; i++) {
      div.textContent += text[i];
      if (i % 3 === 0) chat.scrollTop = chat.scrollHeight;
      await new Promise(r => setTimeout(r, speed));
    }
    chat.scrollTop = chat.scrollHeight;
  }

  function escapeHtml(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

  function addToolCall(container, tc) {
    var div = document.createElement('div');
    div.className = 'tool-call';
    div.innerHTML = '<div class="name">&#128295; ' + tc.name + '</div><div class="args">' + escapeHtml(JSON.stringify(tc.args, null, 2)) + '</div>';
    if (tc.result !== undefined) {
      var cls = tc.result.startsWith('Error') ? 'result error' : 'result';
      div.innerHTML += '<div class="' + cls + '">' + escapeHtml(tc.result.substring(0, 1000)) + '</div>';
    }
    container.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
  }

  function setThinking(el, on) {
    if (!el) return;
    var existing = el.querySelector('.thinking-indicator');
    if (on) {
      if (!existing) {
        var ind = document.createElement('div');
        ind.className = 'thinking-indicator';
        ind.innerHTML = '<div class="loading active" style="display:flex;margin:4px 0"><div class="spinner"></div><span>Thinking...</span></div>';
        el.appendChild(ind);
        chat.scrollTop = chat.scrollHeight;
      }
    } else {
      if (existing) existing.remove();
    }
  }

  async function send() {
    const msg = input.value.trim();
    if (!msg) return;
    input.value = '';
    addMsg('user', msg);
    loading.classList.add('active');
    sendBtn.disabled = true;
    try {
      const res = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({session_id: sessionId, message: msg, role: currentRole})
      });
      if (res.status === 429) {
        addMsg('bot error', 'Rate limit exceeded. Please wait before sending another request.');
        return;
      }
      if (!res.ok) {
        addMsg('bot error', 'Server error: ' + res.status);
        return;
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let botDiv = null;
      let toolCallsData = [];
      let finalResponse = '';
      let streamDone = false;

      while (true) {
        var chunk = await reader.read();
        if (chunk.done) break;
        buffer += decoder.decode(chunk.value, {stream: true});
        var lines = buffer.split('\\n');
        buffer = lines.pop() || '';
        for (var line of lines) {
          line = line.trim();
          if (!line.startsWith('data: ')) continue;
          try {
            var event = JSON.parse(line.slice(6));
          } catch(e) { continue; }

          if (event.type === 'thinking') {
            if (!botDiv) { botDiv = addMsg('bot', ''); }
            setThinking(botDiv, true);
          } else if (event.type === 'tool_call') {
            if (!botDiv) { botDiv = addMsg('bot', ''); }
            setThinking(botDiv, false);
            var tcEntry = {name: event.name, args: event.args};
            toolCallsData.push(tcEntry);
            addToolCall(botDiv, tcEntry);
          } else if (event.type === 'tool_result') {
            var lastTc = toolCallsData[toolCallsData.length - 1];
            if (lastTc) { lastTc.result = event.result; }
            botDiv.textContent = '';
            for (var t of toolCallsData) { addToolCall(botDiv, t); }
            setThinking(botDiv, false);
          } else if (event.type === 'done') {
            finalResponse = event.response || '';
            if (!botDiv) { botDiv = addMsg('bot', ''); }
            setThinking(botDiv, false);
            if (event.extra && event.extra.tool_calls) {
              toolCallsData = event.extra.tool_calls;
              botDiv.textContent = '';
              for (var t of toolCallsData) { addToolCall(botDiv, t); }
              var textDiv = document.createElement('div');
              textDiv.style.marginTop = '8px';
              botDiv.appendChild(textDiv);
              await typeMsg(textDiv, finalResponse);
            } else {
              botDiv.textContent = '';
              await typeMsg(botDiv, finalResponse);
            }
            streamDone = true;
          } else if (event.type === 'error') {
            addMsg('bot error', event.error || 'Stream error');
            streamDone = true;
          }
        }
      }
      if (!streamDone) {
        if (finalResponse) {
          if (!botDiv) { botDiv = addMsg('bot', ''); }
          botDiv.textContent = '';
          await typeMsg(botDiv, finalResponse);
        } else {
          if (!botDiv) { botDiv = addMsg('bot', ''); }
          if (!botDiv.textContent.trim()) botDiv.textContent = 'Done.';
        }
      }
    } catch(e) {
      addMsg('bot error', 'Connection error: ' + e.message);
    } finally {
      loading.classList.remove('active');
      sendBtn.disabled = false;
      input.focus();
    }
  }

  input.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  });
  sendBtn.addEventListener('click', send);

  addMsg('bot', `Hello! I'm the prod-gke AI agent. I can:
- Deploy and manage applications
- Check cluster health
- Run kubectl commands
- Query Prometheus metrics
- Manage monitoring

What would you like me to do?`);

  async function pollHealth() {
    try {
      const res = await fetch('/health');
      const data = await res.json();
      if (data.status === 'ok') {
        healthStatus.textContent = 'All systems healthy';
        healthStatus.className = 'ok';
      } else {
        healthStatus.textContent = 'Degraded: ' + (data.details?.openrouter || 'unknown');
        healthStatus.className = 'warn';
      }
    } catch(e) {
      healthStatus.textContent = 'Disconnected';
      healthStatus.className = 'bad';
    }
  }
  setInterval(pollHealth, 30000);
  pollHealth();
</script>
</body>
</html>"""

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTML

@app.get("/health")
async def health():
    checks = {"status": "ok", "details": {}}
    if OPENROUTER_API_KEY:
        checks["details"]["openrouter"] = "configured"
    else:
        checks["details"]["openrouter"] = "missing_api_key"
    if ROLE_TOKENS:
        loaded = list(ROLE_TOKENS.keys())
        checks["details"]["tokens"] = loaded
    else:
        checks["details"]["tokens"] = "none_loaded"
    if _redis:
        try:
            await _redis.ping()
            checks["details"]["redis"] = "connected"
        except:
            checks["details"]["redis"] = "disconnected"
    else:
        checks["details"]["redis"] = "in-memory"
    checks["details"]["sessions"] = len(sessions)
    return JSONResponse(content=checks, status_code=200)

@app.get("/ready")
async def ready():
    if not OPENROUTER_API_KEY:
        return JSONResponse(content={"status": "not_ready", "reason": "OPENROUTER_API_KEY not set"}, status_code=503)
    if not ROLE_TOKENS:
        return JSONResponse(content={"status": "not_ready", "reason": "no role tokens loaded"}, status_code=503)
    return {"status": "ready", "uptime": time.monotonic()}

@app.post("/api/chat")
async def chat(req: Request):
    body = await req.json()
    msg = body.get("message", "")
    if not msg.strip():
        return JSONResponse(status_code=400, content={"error": "Message is empty"})
    session_id = body.get("session_id", "default")
    role = body.get("role", "admin")

    if role not in ("viewer", "edit", "admin"):
        role = "admin"

    if not _check_rate_limit(session_id):
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded. Please wait before sending another request."},
            headers=_rate_limit_headers(session_id),
        )

    session = await _load_session(session_id)
    if session is None:
        session = {"messages": [], "role": role}

    session["role"] = role
    session["messages"].append({"role": "user", "content": msg.strip()})

    if len(session["messages"]) > MAX_HISTORY * 2:
        session["messages"] = session["messages"][-MAX_HISTORY:]

    try:
        _logger.info("chat_request", extra={"session": session_id[:8], "role": role, "msg_len": len(msg)})
        result = await agent.run(session["messages"], role=role)
        session["messages"] = result["messages"]
        await _save_session(session_id, session)

        return {
            "response": result["response"],
            "extra": result.get("extra", {}),
            "role": role,
            "rate_limit": _rate_limit_headers(session_id),
        }
    except Exception as e:
        _logger.error("chat_error", extra={"session": session_id[:8], "error": str(e)})
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/chat/stream")
async def chat_stream(req: Request):
    body = await req.json()
    msg = body.get("message", "")
    if not msg.strip():
        return JSONResponse(status_code=400, content={"error": "Message is empty"})
    session_id = body.get("session_id", "default")
    role = body.get("role", "admin")

    if role not in ("viewer", "edit", "admin"):
        role = "admin"

    if not _check_rate_limit(session_id):
        headers = _rate_limit_headers(session_id)
        return JSONResponse(status_code=429, content={"error": "Rate limit exceeded."}, headers=headers)

    session = await _load_session(session_id)
    if session is None:
        session = {"messages": [], "role": role}

    session["role"] = role
    session["messages"].append({"role": "user", "content": msg.strip()})

    if len(session["messages"]) > MAX_HISTORY * 2:
        session["messages"] = session["messages"][-MAX_HISTORY:]

    async def event_stream():
        try:
            _logger.info("stream_start", extra={"session": session_id[:8], "role": role, "msg_len": len(msg)})
            async for event in agent.run_stream(session["messages"], role=role):
                data = json.dumps(event)
                yield f"data: {data}\n\n"
                if event.get("type") == "done":
                    session["messages"] = event.get("messages", session["messages"])
                    await _save_session(session_id, session)
                    break
        except Exception as e:
            _logger.error("stream_error", extra={"session": session_id[:8], "error": str(e)})
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
