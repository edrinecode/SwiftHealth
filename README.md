# SwiftHealth Hospital Triage System

Production-oriented, deterministic multi-agent triage system for hospital intake with an optional web front end.

## Safety Principles
- Deterministic orchestrator controls all state transitions.
- Red-flag detection runs before every response.
- Clinical urgency is rule-based and explainable.
- LLM-like response composer controls tone only, not safety decisions.
- Every action appends immutable audit events.

## Run
```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open the front end at `http://localhost:8000/` (or `/dashboard`).

## Environment Variables (especially for AI keys)
1. Copy `.env.example` to `.env`.
2. Put your real keys in `.env` (for example `GEMINI_API_KEY`).
3. **Do not commit `.env`**. Keep it local and configure the same variables in your deployment platform (Railway/Railpack service settings).

```bash
cp .env.example .env
# then edit .env and set your real values
```

For local runs in bash, load variables before starting the server:

```bash
set -a
source .env
set +a
uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
```

## Test
```bash
pytest -q
```

## Disclaimer
This is a triage support tool and not a medical diagnosis.


## Gemini API Key (optional)
- If `GEMINI_API_KEY` is set, SwiftHealth will use Gemini only to polish the wording of responses.
- Triage state transitions, red-flag detection, and urgency classification remain deterministic and rule-based.
- If Gemini is unavailable or times out, responses safely fall back to deterministic text.

## Front End
- `GET /` serves a lightweight triage chat UI for patients/staff.
- The UI calls `POST /api/v1/triage` and displays live session state and urgency.
- `GET /api/v1/config` shows whether Gemini is configured.
