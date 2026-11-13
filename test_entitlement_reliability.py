
from app.agents import entitlement_agent


def test_missing_gemini_configuration_escalates(monkeypatch):
    monkeypatch.setattr(
        entitlement_agent,
        "load_dotenv",
        lambda **kwargs: None
    )

    monkeypatch.delenv("MODEL_NAME", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    result = entitlement_agent.evaluate_entitlement(
        {"description": "My flight was cancelled."},
        {"disruption_type": "cancellation"},
        search_function=lambda query: [],
        clause_function=lambda clause_id: {}
    )

    assert result["route"] == "request-further-evidence"
    assert result["human_escalation"] is True
    assert result["verification_passed"] is False
    assert result["citation_verification"]["status"] == "not_run"


def test_missing_retrieval_system_escalates():
    result = entitlement_agent.evaluate_entitlement(
        {"description": "My flight was cancelled."},
        {"disruption_type": "cancellation"}
    )

    assert result["route"] == "request-further-evidence"
    assert result["human_escalation"] is True
    assert result["verification_passed"] is False
    assert result["retrieved_passages"] == []

