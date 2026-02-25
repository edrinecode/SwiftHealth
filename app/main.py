from __future__ import annotations

from app.models import MessageRequest, MessageResponse
from app.orchestrator import TriageOrchestrator

orchestrator = TriageOrchestrator()

DASHBOARD_HTML = """
<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>SwiftHealth Triage Console</title>
  <style>
    :root { color-scheme: light; }
    body { margin: 0; font-family: Inter, Arial, sans-serif; background: #f3f6fb; color: #102030; }
    .wrap { max-width: 980px; margin: 0 auto; padding: 1.5rem; }
    .hero { background: linear-gradient(120deg, #0f5ed7, #19a6d1); color: #fff; border-radius: 14px; padding: 1.2rem 1.4rem; }
    .hero h1 { margin: 0 0 .3rem; font-size: 1.35rem; }
    .badge { display:inline-block; background: rgba(255,255,255,.2); border-radius: 999px; padding: .2rem .6rem; font-size:.83rem; }
    .grid { margin-top: 1rem; display: grid; grid-template-columns: 2fr 1fr; gap: 1rem; }
    .card { background:#fff; border-radius: 12px; box-shadow: 0 2px 10px rgba(15,38,71,.08); padding: 1rem; }
    #chat { min-height: 420px; max-height: 60vh; overflow: auto; border: 1px solid #e3e9f3; border-radius: 10px; padding: .7rem; }
    .msg { margin: .6rem 0; padding: .55rem .7rem; border-radius: 10px; line-height: 1.35; }
    .user { background: #e9f3ff; margin-left: 10%; }
    .bot { background: #f5f7fb; margin-right: 10%; }
    form { display:flex; gap:.5rem; margin-top:.7rem; }
    input, button { font-size: .95rem; border-radius: 8px; border: 1px solid #d4dceb; padding: .55rem .6rem; }
    #message { flex:1; }
    button { background: #0f5ed7; color: white; border: 0; cursor: pointer; }
    dl { margin:0; }
    dt { font-size: .8rem; color:#6e7d95; margin-top:.5rem; }
    dd { margin: .1rem 0 .2rem; font-weight: 600; }
    .footnote { margin-top: .7rem; font-size: .82rem; color:#4d607d; }
    @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <h1>SwiftHealth Triage Front End</h1>
      <div class="badge" id="modelBadge">Loading AI mode...</div>
      <p style="margin:.45rem 0 0; font-size:.92rem;">Deterministic triage logic is always enforced. AI mode only refines wording.</p>
    </div>

    <div class="grid">
      <section class="card">
        <h3 style="margin:.1rem 0 .5rem;">Patient Chat</h3>
        <div id="chat"></div>
        <form id="triageForm">
          <input id="message" placeholder="Describe symptoms, e.g. chest pain and shortness of breath" autocomplete="off" required />
          <button type="submit">Send</button>
        </form>
        <p class="footnote">This is a triage support tool and not a medical diagnosis.</p>
      </section>

      <aside class="card">
        <h3 style="margin:.1rem 0 .5rem;">Live Session Summary</h3>
        <dl>
          <dt>Session ID</dt><dd id="sessionId"></dd>
          <dt>State</dt><dd id="state">-</dd>
          <dt>Urgency</dt><dd id="urgency">-</dd>
          <dt>Risk Score</dt><dd id="risk">-</dd>
          <dt>Next Question</dt><dd id="nextQ">-</dd>
          <dt>Rules Triggered</dt><dd id="rules">-</dd>
        </dl>
      </aside>
    </div>
  </div>

<script>
const sid = 'web-' + Math.random().toString(36).slice(2, 10);
document.getElementById('sessionId').textContent = sid;
const chat = document.getElementById('chat');

function addMessage(role, text) {
  const div = document.createElement('div');
  div.className = `msg ${role}`;
  div.textContent = text;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

function updateSummary(s) {
  document.getElementById('state').textContent = s.state || '-';
  document.getElementById('urgency').textContent = s.urgency_level || '-';
  document.getElementById('risk').textContent = Number(s.risk_score || 0).toFixed(2);
  document.getElementById('nextQ').textContent = s.next_question || '-';
  document.getElementById('rules').textContent = (s.triggered_rules || []).join(', ') || '-';
}

fetch('/api/v1/config').then(r => r.json()).then(cfg => {
  const label = cfg.gemini_enabled ? `Gemini enabled (${cfg.gemini_model})` : 'Gemini not configured (deterministic text mode)';
  document.getElementById('modelBadge').textContent = label;
});

addMessage('bot', 'Welcome. Please tell me what symptoms or concern you are having today.');

document.getElementById('triageForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const input = document.getElementById('message');
  const message = input.value.trim();
  if (!message) return;
  addMessage('user', message);
  input.value = '';

  const res = await fetch('/api/v1/triage', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ session_id: sid, patient_id: 'web-patient', message }),
  });
  const data = await res.json();
  addMessage('bot', data.response || 'No response generated.');
  if (data.session) updateSummary(data.session);
});
</script>
</body>
</html>
"""


try:
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse

    app = FastAPI(title="SwiftHealth Hospital Triage", version="1.0.0")

    @app.get("/")
    def home() -> HTMLResponse:
        return HTMLResponse(DASHBOARD_HTML)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/config")
    def config() -> dict[str, str | bool]:
        return {
            "gemini_enabled": orchestrator.tone_polisher.enabled,
            "gemini_model": orchestrator.tone_polisher.model,
        }

    @app.post("/api/v1/triage")
    def triage(request: MessageRequest) -> dict:
        response = orchestrator.process_message(request.session_id, request.patient_id, request.message)
        return {"session": response.session.to_dict(), "response": response.response, "disclaimer": response.disclaimer}

    @app.get("/api/v1/sessions/{session_id}")
    def session(session_id: str):
        session_data = orchestrator.sessions.get(session_id)
        return None if session_data is None else session_data.to_dict()

    @app.get("/dashboard", response_class=HTMLResponse)
    def dashboard() -> str:
        return DASHBOARD_HTML

except ModuleNotFoundError:
    app = None


def triage_message(session_id: str, patient_id: str | None, message: str) -> MessageResponse:
    return orchestrator.process_message(session_id, patient_id, message)
