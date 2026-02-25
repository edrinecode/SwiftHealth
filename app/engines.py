from __future__ import annotations

from dataclasses import dataclass
import re

from app.models import IntentType, SessionData, UrgencyLevel


EMERGENCY_PHRASES = {
    "difficulty breathing": "difficulty_breathing",
    "can't breathe": "difficulty_breathing",
    "chest pain": "chest_pain",
    "severe bleeding": "severe_bleeding",
    "loss of consciousness": "loss_of_consciousness",
    "unconscious": "loss_of_consciousness",
    "stroke": "stroke_symptoms",
    "face drooping": "stroke_symptoms",
    "seizure": "seizure",
    "anaphylaxis": "severe_allergic_reaction",
    "throat closing": "severe_allergic_reaction",
    "altered mental": "altered_mental_state",
    "collapsed": "collapse",
    "i'm dying": "im_dying",
    "im dying": "im_dying",
}

GREETING_TERMS = {"hi", "hello", "hey", "good morning", "good afternoon"}
ADMIN_TERMS = {"hours", "billing", "insurance", "location", "address"}
APPOINTMENT_TERMS = {"appointment", "schedule", "book"}
SYMPTOM_TERMS = {
    "pain",
    "fever",
    "cough",
    "nausea",
    "vomit",
    "dizzy",
    "headache",
    "pregnan",
    "rash",
    "allergic",
    "breath",
    "cold",
    "symptom",
    "triage",
}


@dataclass
class IntentResult:
    intent: IntentType
    confidence: float


class IntentClassifier:
    def classify(self, message: str) -> IntentResult:
        text = message.lower().strip()
        if any(re.search(rf"\b{re.escape(term)}\b", text) for term in GREETING_TERMS):
            return IntentResult(IntentType.greeting, 0.95)
        if any(term in text for term in APPOINTMENT_TERMS):
            return IntentResult(IntentType.appointment_request, 0.9)
        if any(term in text for term in ADMIN_TERMS):
            return IntentResult(IntentType.admin_question, 0.85)
        if any(term in text for term in SYMPTOM_TERMS):
            return IntentResult(IntentType.medical_symptom, 0.85)
        return IntentResult(IntentType.unclear, 0.4)


class RedFlagEngine:
    def detect(self, message: str, session: SessionData) -> list[str]:
        text = message.lower()
        triggered = [label for phrase, label in EMERGENCY_PHRASES.items() if phrase in text]
        if "throat" in text and ("closing" in text or "closed" in text):
            triggered.append("severe_allergic_reaction")
        if session.demographics.age is not None and session.demographics.age < 1:
            if "fever" in text and any(temp in text for temp in ["104", "40", "high fever"]):
                triggered.append("high_fever_in_infant")
        return sorted(set(triggered))


class ClinicalRulesEngine:
    def classify(self, session: SessionData) -> tuple[UrgencyLevel, list[str], float]:
        rules: list[str] = []

        if session.red_flags_detected:
            return UrgencyLevel.EMERGENCY, [f"red_flag:{f}" for f in session.red_flags_detected], 1.0

        complaint = session.chief_complaint.lower()
        assoc = " ".join(session.associated_symptoms).lower()

        if "chest pain" in complaint and (session.demographics.age or 0) > 40:
            rules.append("chest_pain_age_over_40")
            return UrgencyLevel.URGENT, rules, 0.92

        if "fever" in complaint and "stiff neck" in assoc:
            rules.append("fever_with_stiff_neck")
            return UrgencyLevel.EMERGENCY, rules, 0.97

        if "allergic" in complaint and session.severity and session.severity >= 8:
            rules.append("severe_allergy_high_severity")
            return UrgencyLevel.URGENT, rules, 0.88

        if "abdominal pain" in complaint and session.demographics.pregnancy_status == "pregnant":
            rules.append("abdominal_pain_during_pregnancy")
            return UrgencyLevel.URGENT, rules, 0.9

        if "cold" in complaint and (session.symptom_onset or "").lower() in {"1 day", "2 days", "3 days"}:
            rules.append("mild_cold_under_3_days")
            return UrgencyLevel.ROUTINE, rules, 0.8

        if session.severity is not None and session.severity >= 8:
            rules.append("high_symptom_severity")
            return UrgencyLevel.URGENT, rules, 0.82

        rules.append("default_routine_conservative")
        return UrgencyLevel.ROUTINE, rules, 0.65


class RiskScoringAgent:
    def score(self, session: SessionData) -> float:
        base = 0.1
        if session.severity:
            base += min(session.severity / 15.0, 0.6)
        if session.demographics.age and session.demographics.age > 65:
            base += 0.15
        if session.chronic_conditions:
            base += 0.1
        return min(base, 0.95)
