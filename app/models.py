from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class TriageState(str, Enum):
    IDLE = "IDLE"
    GREETING = "GREETING"
    INTAKE = "INTAKE"
    TRIAGE = "TRIAGE"
    EMERGENCY = "EMERGENCY"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"


class IntentType(str, Enum):
    greeting = "greeting"
    medical_symptom = "medical_symptom"
    appointment_request = "appointment_request"
    admin_question = "admin_question"
    unclear = "unclear"


class UrgencyLevel(str, Enum):
    EMERGENCY = "EMERGENCY"
    URGENT = "URGENT"
    ROUTINE = "ROUTINE"


@dataclass
class AuditEvent:
    timestamp: str
    event_type: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class Demographics:
    age: int | None = None
    sex: str | None = None
    pregnancy_status: str | None = None


@dataclass
class SessionData:
    session_id: str
    patient_id: str | None = None
    state: TriageState = TriageState.IDLE
    demographics: Demographics = field(default_factory=Demographics)
    chief_complaint: str = ""
    symptoms: list[str] = field(default_factory=list)
    associated_symptoms: list[str] = field(default_factory=list)
    chronic_conditions: list[str] = field(default_factory=list)
    medications: list[str] = field(default_factory=list)
    allergies: list[str] = field(default_factory=list)
    symptom_onset: str | None = None
    severity: int | None = None
    red_flags_detected: list[str] = field(default_factory=list)
    urgency_level: UrgencyLevel | None = None
    risk_score: float = 0.0
    recommended_action: str = ""
    triggered_rules: list[str] = field(default_factory=list)
    confidence: float = 0.0
    next_question: str | None = None
    uncertainty: float = 0.0
    audit_log: list[AuditEvent] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MessageRequest:
    session_id: str
    patient_id: str | None
    message: str


@dataclass
class MessageResponse:
    session: SessionData
    response: str
    disclaimer: str = "This is a triage support tool and not a medical diagnosis."
