from __future__ import annotations

from app.models import MessageRequest, MessageResponse
from app.orchestrator import TriageOrchestrator

orchestrator = TriageOrchestrator()

DASHBOARD_HTML = """
<!doctype html>
<html>
<head>
  <title>SwiftHealth Triage Dashboard</title>
  <style>
    body { font-family: Arial, sans-serif; background: #f4f7fb; color: #102030; padding: 2rem; }
    .card { background: white; border-radius: 10px; padding: 1rem 1.5rem; margin-bottom: 1rem; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
    h1 { margin-top: 0; }
    .badge { padding: 0.2rem 0.5rem; border-radius: 6px; background: #e7eef9; }
  </style>
</head>
<body>
  <h1>SwiftHealth Admin Dashboard</h1>
  <p class="badge">Deterministic state machine enabled</p>
  <div class="card">
    <h3>Safety Controls</h3>
    <ul>
      <li>Red-flag checks run before all responses</li>
      <li>Rule-based urgency classification only</li>
      <li>Immutable audit log events recorded per transition</li>
    </ul>
  </div>
  <div class="card">
    <h3>Compliance Notice</h3>
    <p>This is a triage support tool and not a medical diagnosis.</p>
  </div>
</body>
</html>
"""


try:
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse

    app = FastAPI(title="SwiftHealth Hospital Triage", version="1.0.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

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
