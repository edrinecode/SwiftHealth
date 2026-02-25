from app.models import TriageState, UrgencyLevel
from app.orchestrator import TriageOrchestrator


def run_conversation(orchestrator: TriageOrchestrator, session_id: str, messages: list[str]):
    responses = []
    for msg in messages:
        responses.append(orchestrator.process_message(session_id=session_id, patient_id="p1", message=msg))
    return responses


def test_chest_pain_red_flag_emergency_override():
    o = TriageOrchestrator()
    res = o.process_message("s1", "p1", "I have chest pain and trouble breathing")
    assert res.session.urgency_level == UrgencyLevel.EMERGENCY
    assert "red_flag:chest_pain" in res.session.triggered_rules
    assert res.session.state == TriageState.CLOSED


def test_stroke_symptoms_trigger_emergency():
    o = TriageOrchestrator()
    res = o.process_message("s2", "p1", "My face is drooping and I think stroke symptoms")
    assert res.session.urgency_level == UrgencyLevel.EMERGENCY
    assert any("stroke" in r for r in res.session.triggered_rules)


def test_pediatric_fever_emergency():
    o = TriageOrchestrator()
    o.process_message("s3", "p1", "I need symptom triage")
    o.process_message("s3", "p1", "10 months old")
    res = o.process_message("s3", "p1", "high fever 104")
    assert res.session.urgency_level == UrgencyLevel.EMERGENCY
    assert any("high_fever_in_infant" in r for r in res.session.triggered_rules)


def test_allergic_reaction_emergency():
    o = TriageOrchestrator()
    res = o.process_message("s4", "p1", "My throat is closing, severe allergic reaction")
    assert res.session.urgency_level == UrgencyLevel.EMERGENCY


def test_minor_cold_routine_path():
    o = TriageOrchestrator()
    msgs = [
        "I have cold symptoms",
        "28",
        "female",
        "not pregnant",
        "mild cold",
        "2 days",
        "3",
        "runny nose",
        "none",
        "none",
        "none",
    ]
    responses = run_conversation(o, "s5", msgs)
    last = responses[-1]
    assert last.session.urgency_level == UrgencyLevel.ROUTINE
    assert "mild_cold_under_3_days" in last.session.triggered_rules


def test_abdominal_pain_pregnancy_urgent():
    o = TriageOrchestrator()
    msgs = [
        "I have pain",
        "32",
        "female",
        "pregnant",
        "abdominal pain",
        "1 day",
        "6",
        "nausea",
        "none",
        "prenatal vitamins",
        "penicillin",
    ]
    responses = run_conversation(o, "s6", msgs)
    assert responses[-1].session.urgency_level == UrgencyLevel.URGENT
    assert "abdominal_pain_during_pregnancy" in responses[-1].session.triggered_rules


def test_greeting_only_conversation():
    o = TriageOrchestrator()
    res = o.process_message("s7", "p1", "Hello")
    assert "welcome" in res.response.lower()
    assert res.session.state == TriageState.GREETING


def test_one_question_at_a_time_flow():
    o = TriageOrchestrator()
    start = o.process_message("s8", "p1", "I have headache")
    assert start.session.state == TriageState.TRIAGE
    assert start.response.count("?") == 1


def test_audit_log_integrity_and_no_diagnosis_text():
    o = TriageOrchestrator()
    res = o.process_message("s9", "p1", "I have chest pain")
    assert len(res.session.audit_log) > 3
    for event in res.session.audit_log:
        assert event.timestamp
    assert "diagnosis" not in res.response.lower()


def test_name_question_gets_identity_response():
    o = TriageOrchestrator()
    o.process_message("s10", "p1", "hi")
    res = o.process_message("s10", "p1", "what ur name?")
    assert "swifthealth" in res.response.lower()


def test_admin_question_shortcuts_are_classified():
    o = TriageOrchestrator()
    res = o.process_message("s11", "p1", "admin qn")
    assert res.session.state == TriageState.INTAKE
    assert "route appointments" in res.response.lower()
