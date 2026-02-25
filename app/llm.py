from __future__ import annotations

import json
import os
from urllib import error, request


class GeminiTonePolisher:
    """Optional Gemini-backed tone polisher.

    Safety/triage decisions remain deterministic in orchestrator logic.
    This class only rewrites wording when configured.
    """

    def __init__(self) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip() or "gemini-1.5-flash"
        self.timeout_s = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "4"))

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def polish(self, draft: str) -> str:
        if not self.enabled:
            return draft

        prompt = (
            "Rewrite the following hospital triage assistant reply for clarity and empathy. "
            "Keep it concise, keep all safety instructions intact, do not add diagnosis, "
            "and preserve the original intent exactly. Return only the rewritten response.\n\n"
            f"Original: {draft}"
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 180,
            },
        }

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        req = request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout_s) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except (error.URLError, TimeoutError, ValueError, json.JSONDecodeError):
            return draft

        candidates = body.get("candidates") or []
        if not candidates:
            return draft
        parts = (((candidates[0] or {}).get("content") or {}).get("parts")) or []
        if not parts:
            return draft
        text = (parts[0] or {}).get("text", "").strip()
        return text or draft
