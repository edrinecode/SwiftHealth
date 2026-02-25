# SwiftHealth Hospital Triage System

Production-oriented, deterministic multi-agent triage backend for hospital intake.

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

## Environment Variables (especially for AI keys)
1. Copy `.env.example` to `.env`.
2. Put your real keys in `.env` (for example `OPENAI_API_KEY`).
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
