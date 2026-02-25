from __future__ import annotations

from app.models import SessionData, TriageState, UrgencyLevel


class FrontDeskAgent:
    def respond(self) -> str:
        return (
            "Hello, and welcome. I can help with triage intake and route you to the right level of care. "
            "Please tell me what symptoms or concern you are having today."
        )


class TriageAgent:
    QUESTION_FLOW = [
        ("age", "Thanks. What is your age?"),
        ("sex", "Got it. What sex were you assigned at birth?"),
        ("pregnancy_status", "Okay. Are you currently pregnant, possibly pregnant, or not pregnant?"),
        ("chief_complaint", "Please describe your main symptom or concern in one sentence."),
        ("symptom_onset", "When did this start?"),
        ("severity", "On a scale of 1 to 10, how severe is it right now?"),
        ("associated_symptoms", "Any other symptoms with this, like fever, dizziness, weakness, or vomiting?"),
        ("chronic_conditions", "Do you have any chronic medical conditions?"),
        ("medications", "What medications are you currently taking?"),
        ("allergies", "Any medication or food allergies?"),
    ]

    def next_question(self, session: SessionData) -> str | None:
        for field, question in self.QUESTION_FLOW:
            if field == "age" and session.demographics.age is None:
                return question
            if field == "sex" and session.demographics.sex is None:
                return question
            if field == "pregnancy_status" and session.demographics.pregnancy_status is None:
                return question
            if field == "chief_complaint" and not session.chief_complaint:
                return question
            if field == "symptom_onset" and session.symptom_onset is None:
                return question
            if field == "severity" and session.severity is None:
                return question
            if field == "associated_symptoms" and not session.associated_symptoms:
                return question
            if field == "chronic_conditions" and not session.chronic_conditions:
                return question
            if field == "medications" and not session.medications:
                return question
            if field == "allergies" and not session.allergies:
                return question
        return None


class EscalationAgent:
    def recommend(self, urgency: UrgencyLevel) -> str:
        if urgency == UrgencyLevel.EMERGENCY:
            return (
                "I'm very concerned about what you're describing. Seek immediate medical care now. "
                "Call emergency services or go to the nearest emergency department immediately."
            )
        if urgency == UrgencyLevel.URGENT:
            return (
                "Based on your triage responses, you should be evaluated within 24 hours. "
                "I can help route you to urgent appointment scheduling."
            )
        return (
            "This appears suitable for routine follow-up. Please book a standard appointment. "
            "If symptoms worsen, seek urgent care promptly."
        )


class ResponseComposer:
    def compose(
        self,
        state: TriageState,
        urgency_level: UrgencyLevel | None,
        next_question: str | None,
        red_flag_detected: bool,
        recommended_action: str,
        conversation_history_summary: str,
    ) -> str:
        if red_flag_detected and urgency_level == UrgencyLevel.EMERGENCY:
            return recommended_action
        if state in {TriageState.GREETING, TriageState.IDLE}:
            return "Thanks for reaching out. " + (next_question or "How can I help today?")
        if state == TriageState.TRIAGE and next_question:
            prefix = "Thanks. " if conversation_history_summary else "Okay. "
            return f"{prefix}{next_question}"
        if state in {TriageState.ESCALATED, TriageState.CLOSED} and recommended_action:
            return f"Thanks for sharing this information. {recommended_action}"
        return "Thanks. Could you clarify your main concern so I can triage safely?"
