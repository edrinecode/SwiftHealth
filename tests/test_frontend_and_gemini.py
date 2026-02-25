from app.llm import GeminiTonePolisher
from app.main import DASHBOARD_HTML


def test_gemini_polisher_without_key_returns_draft(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    polisher = GeminiTonePolisher()
    draft = "Please seek urgent care now."
    assert polisher.enabled is False
    assert polisher.polish(draft) == draft


def test_frontend_html_contains_chat_ui_sections():
    assert "SwiftHealth Triage Front End" in DASHBOARD_HTML
    assert "Patient Chat" in DASHBOARD_HTML
    assert "/api/v1/triage" in DASHBOARD_HTML
