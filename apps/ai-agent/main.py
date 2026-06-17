from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import os, json

from agent import Agent

MAX_SESSIONS = int(os.environ.get("MAX_SESSIONS", "100"))
MAX_HISTORY = int(os.environ.get("MAX_HISTORY", "20"))

app = FastAPI(title="prod-gke AI Agent")

agent = Agent()
sessions = {}

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>prod-gke AI Agent</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:#0d1117; color:#c9d1d9; height:100vh; display:flex; flex-direction:column; }
  .header { background:#161b22; border-bottom:1px solid #30363d; padding:16px 24px; display:flex; align-items:center; gap:12px; }
  .header h1 { font-size:18px; font-weight:600; color:#f0f6fc; }
  .header span { font-size:12px; color:#8b949e; background:#21262d; padding:2px 8px; border-radius:10px; }
  .status { margin-left:auto; display:flex; align-items:center; gap:6px; font-size:13px; }
  .status-dot { width:8px; height:8px; border-radius:50%; background:#3fb950; }
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
</style>
</head>
<body>
<div class="header">
  <h1>prod-gke AI Agent</h1>
  <span>OpenRouter</span>
  <div class="status">
    <div class="status-dot"></div>
    <span>Cluster Connected</span>
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
  function genId() { try { return crypto.randomUUID(); } catch(e) { return Date.now().toString(36) + Math.random().toString(36).slice(2); } }
  let sessionId = localStorage.getItem('sessionId') || genId();
  localStorage.setItem('sessionId', sessionId);

  function addMsg(type, content, extra) {
    const div = document.createElement('div');
    div.className = 'msg ' + type;
    if (extra) div.dataset.extra = JSON.stringify(extra);
    if (type === 'bot' && extra?.tool_calls) {
      let html = content;
      for (const tc of extra.tool_calls) {
        html += '<div class="tool-call"><div class="name">🔧 ' + tc.name + '</div><div class="args">' + escapeHtml(JSON.stringify(tc.args, null, 2)) + '</div>';
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
  }

  function escapeHtml(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

  async function send() {
    const msg = input.value.trim();
    if (!msg) return;
    input.value = '';
    addMsg('user', msg);
    loading.classList.add('active');
    sendBtn.disabled = true;
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({session_id: sessionId, message: msg})
      });
      const data = await res.json();
      if (data.error) { addMsg('bot error', data.error); return; }
      addMsg('bot', data.response, data.extra || {});
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
</script>
</body>
</html>"""

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTML

@app.post("/api/chat")
async def chat(req: Request):
    body = await req.json()
    msg = body.get("message", "")
    if not msg.strip():
        return JSONResponse(status_code=400, content={"error": "Message is empty"})
    session_id = body.get("session_id", "default")

    if len(sessions) >= MAX_SESSIONS:
        oldest = min(sessions.keys(), key=lambda k: len(sessions[k]))
        del sessions[oldest]

    if session_id not in sessions:
        sessions[session_id] = []
    sessions[session_id].append({"role": "user", "content": msg.strip()})

    if len(sessions[session_id]) > MAX_HISTORY * 2:
        sessions[session_id] = sessions[session_id][-MAX_HISTORY:]

    try:
        result = await agent.run(sessions[session_id])
        sessions[session_id] = result["messages"]
        return {"response": result["response"], "extra": result.get("extra", {})}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
