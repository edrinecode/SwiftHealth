from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.agents import EscalationAgent, FrontDeskAgent, ResponseComposer, TriageAgent
from app.engines import ClinicalRulesEngine, IntentClassifier, RedFlagEngine, RiskScoringAgent
from app.llm import GeminiTonePolisher
from app.models import AuditEvent, IntentType, MessageResponse, SessionData, TriageState, UrgencyLevel


class TriageOrchestrator:
    def __init__(self) -> None:
        self.sessions: dict[str, SessionData] = {}
        self.intent_classifier = IntentClassifier()
        self.front_desk_agent = FrontDeskAgent()
        self.triage_agent = TriageAgent()
        self.red_flag_engine = RedFlagEngine()
        self.rules_engine = ClinicalRulesEngine()
        self.risk_agent = RiskScoringAgent()
        self.escalation_agent = EscalationAgent()
        self.response_composer = ResponseComposer()
        self.tone_polisher = GeminiTonePolisher()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _log(self, session: SessionData, event_type: str, details: dict[str, Any]) -> None:
        session.audit_log.append(AuditEvent(timestamp=self._now(), event_type=event_type, details=details))
        session.timestamp = self._now()

    def _transition(self, session: SessionData, new_state: TriageState, reason: str) -> None:
        old = session.state
        if old != new_state:
            session.state = new_state
            self._log(session, "state_transition", {"from": old.value, "to": new_state.value, "reason": reason})

    def _extract_triage_fields(self, session: SessionData, message: str) -> None:
        text = message.strip()
        lowered = text.lower()

        if session.demographics.age is None:
            digits = "".join(ch for ch in text if ch.isdigit())
            if digits:
                numeric_age = int(digits)
                if "month" in lowered:
                    session.demographics.age = 0
                    self._log(session, "data_update", {"field": "demographics.age", "value": 0, "unit": "months"})
                else:
                    session.demographics.age = numeric_age
                    self._log(session, "data_update", {"field": "demographics.age", "value": session.demographics.age})
                return

        words = set(lowered.replace(",", " ").split())

        if session.demographics.sex is None and any(x in words for x in ["male", "female", "intersex"]):
            session.demographics.sex = "male" if "male" in words else "female" if "female" in words else "intersex"
            self._log(session, "data_update", {"field": "demographics.sex", "value": session.demographics.sex})
            return

        if session.demographics.pregnancy_status is None and any(
            x in lowered for x in ["pregnant", "not pregnant", "possibly pregnant"]
        ):
            if "possibly" in lowered:
                session.demographics.pregnancy_status = "possibly pregnant"
            elif "not" in lowered:
                session.demographics.pregnancy_status = "not pregnant"
            else:
                session.demographics.pregnancy_status = "pregnant"
            self._log(
                session,
                "data_update",
                {"field": "demographics.pregnancy_status", "value": session.demographics.pregnancy_status},
            )
            return

        if not session.chief_complaint:
            session.chief_complaint = text
            session.symptoms.append(text)
            self._log(session, "data_update", {"field": "chief_complaint", "value": session.chief_complaint})
            return

        if session.symptom_onset is None:
            session.symptom_onset = text
            self._log(session, "data_update", {"field": "symptom_onset", "value": session.symptom_onset})
            return

        if session.severity is None:
            digits = [int(tok) for tok in lowered.replace("/", " ").split() if tok.isdigit()]
            if digits:
                session.severity = max(1, min(10, digits[0]))
                self._log(session, "data_update", {"field": "severity", "value": session.severity})
                return

        if not session.associated_symptoms:
            session.associated_symptoms = [part.strip() for part in text.split(",") if part.strip()]
            self._log(session, "data_update", {"field": "associated_symptoms", "value": session.associated_symptoms})
            return

        if not session.chronic_conditions:
            session.chronic_conditions = [part.strip() for part in text.split(",") if part.strip()]
            self._log(session, "data_update", {"field": "chronic_conditions", "value": session.chronic_conditions})
            return

        if not session.medications:
            session.medications = [part.strip() for part in text.split(",") if part.strip()]
            self._log(session, "data_update", {"field": "medications", "value": session.medications})
            return

        if not session.allergies:
            session.allergies = [part.strip() for part in text.split(",") if part.strip()]
            self._log(session, "data_update", {"field": "allergies", "value": session.allergies})

    def process_message(self, session_id: str, patient_id: str | None, message: str) -> MessageResponse:
        session = self.sessions.get(session_id)
        if not session:
            session = SessionData(session_id=session_id, patient_id=patient_id)
            self.sessions[session_id] = session
            self._log(session, "session_created", {"patient_id": patient_id})

        self._log(session, "user_message", {"message": message})

        red_flags = self.red_flag_engine.detect(message, session)
        if red_flags:
            session.red_flags_detected = list(sorted(set(session.red_flags_detected + red_flags)))
            session.urgency_level = UrgencyLevel.EMERGENCY
            session.triggered_rules = [f"red_flag:{flag}" for flag in session.red_flags_detected]
            session.confidence = 1.0
            session.recommended_action = self.escalation_agent.recommend(UrgencyLevel.EMERGENCY)
            self._log(session, "red_flag_triggered", {"red_flags": red_flags})
            self._transition(session, TriageState.EMERGENCY, "red_flag_override")
            self._transition(session, TriageState.ESCALATED, "emergency_handoff")
            response = self.response_composer.compose(
                session.state,
                session.urgency_level,
                None,
                True,
                session.recommended_action,
                "",
            )
            self._transition(session, TriageState.CLOSED, "emergency_session_terminated")
            response = self.tone_polisher.polish(response)
            self._log(session, "assistant_message", {"message": response})
            return MessageResponse(session=session, response=response)

        if session.state in {TriageState.IDLE, TriageState.GREETING, TriageState.INTAKE}:
            if self.front_desk_agent.is_name_question(message):
                self._transition(session, TriageState.GREETING, "assistant_identity_requested")
                text = self.front_desk_agent.respond_to_name_question()
                text = self.tone_polisher.polish(text)
                self._log(session, "assistant_message", {"message": text})
                return MessageResponse(session=session, response=text)

            intent = self.intent_classifier.classify(message)
            self._log(session, "intent_classified", {"intent": intent.intent.value, "confidence": intent.confidence})
            if intent.intent == IntentType.greeting:
                self._transition(session, TriageState.GREETING, "greeting_detected")
                text = self.front_desk_agent.respond()
                text = self.tone_polisher.polish(text)
                self._log(session, "assistant_message", {"message": text})
                return MessageResponse(session=session, response=text)
            if intent.intent in {IntentType.admin_question, IntentType.appointment_request}:
                self._transition(session, TriageState.INTAKE, "non_clinical_intake")
                text = "I can help route appointments and triage concerns. If you have symptoms, please describe them briefly."
                text = self.tone_polisher.polish(text)
                self._log(session, "assistant_message", {"message": text})
                return MessageResponse(session=session, response=text)
            if intent.intent == IntentType.unclear:
                self._transition(session, TriageState.INTAKE, "clarification_needed")
                text = "Thanks. Could you share whether you need symptom triage, an appointment, or an admin question?"
                text = self.tone_polisher.polish(text)
                self._log(session, "assistant_message", {"message": text})
                return MessageResponse(session=session, response=text)
            self._transition(session, TriageState.TRIAGE, "medical_intent_detected")
            first_question = self.triage_agent.next_question(session)
            session.next_question = first_question
            response = self.response_composer.compose(
                session.state,
                session.urgency_level,
                first_question,
                False,
                "",
                "",
            )
            response = self.tone_polisher.polish(response)
            self._log(session, "assistant_message", {"message": response})
            return MessageResponse(session=session, response=response)

        if session.state == TriageState.TRIAGE:
            self._extract_triage_fields(session, message)
            session.risk_score = self.risk_agent.score(session)
            if session.uncertainty > 0.7:
                session.urgency_level = UrgencyLevel.URGENT
                session.recommended_action = self.escalation_agent.recommend(UrgencyLevel.URGENT)
                self._transition(session, TriageState.ESCALATED, "high_uncertainty_human_escalation")
            else:
                next_q = self.triage_agent.next_question(session)
                session.next_question = next_q
                if next_q:
                    response = self.response_composer.compose(
                        session.state,
                        session.urgency_level,
                        next_q,
                        False,
                        "",
                        "summary",
                    )
                    response = self.tone_polisher.polish(response)
                    self._log(session, "assistant_message", {"message": response})
                    return MessageResponse(session=session, response=response)

                urgency, rules, confidence = self.rules_engine.classify(session)
                session.urgency_level = urgency
                session.triggered_rules = rules
                session.confidence = confidence
                session.recommended_action = self.escalation_agent.recommend(urgency)
                self._log(
                    session,
                    "rules_classified",
                    {"urgency_level": urgency.value, "triggered_rules": rules, "confidence": confidence},
                )
                self._transition(session, TriageState.ESCALATED, "triage_completed")

        if session.state == TriageState.ESCALATED:
            response = self.response_composer.compose(
                session.state,
                session.urgency_level,
                None,
                False,
                session.recommended_action,
                "summary",
            )
            self._transition(session, TriageState.CLOSED, "handoff_completed")
            response = self.tone_polisher.polish(response)
            self._log(session, "assistant_message", {"message": response})
            return MessageResponse(session=session, response=response)

        fallback = "I’m unable to continue safely in this session. Seek immediate medical care now."
        fallback = self.tone_polisher.polish(fallback)
        self._log(session, "failsafe_triggered", {"message": fallback})
        session.urgency_level = UrgencyLevel.EMERGENCY
        session.recommended_action = fallback
        self._transition(session, TriageState.CLOSED, "failsafe")
        return MessageResponse(session=session, response=fallback)
