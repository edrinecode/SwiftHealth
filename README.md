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

## Test
```bash
pytest -q
```

## Disclaimer
This is a triage support tool and not a medical diagnosis.
