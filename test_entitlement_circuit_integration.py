from unittest.mock import Mock

import pytest

from app.agents import entitlement_agent
from app.agents.reliability import CircuitBreaker


def test_open_circuit_uses_fallback(monkeypatch):
    monkeypatch.setenv("MODEL_NAME", "test-model")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

    monkeypatch.setattr(
        entitlement_agent,
        "load_dotenv",
        lambda **kwargs: None
    )

    breaker = CircuitBreaker(
        failure_threshold=1,
        recovery_timeout=30
    )

    def failing_call():
        raise RuntimeError("503 UNAVAILABLE")

    with pytest.raises(RuntimeError):
        breaker.call(failing_call)

    assert breaker.state == "open"

    monkeypatch.setattr(
        entitlement_agent,
        "GEMINI_CIRCUIT_BREAKER",
        breaker
    )

    planner = Mock()

    model = Mock()
    model.with_structured_output.return_value = planner

    monkeypatch.setattr(
        entitlement_agent,
        "ChatGoogleGenerativeAI",
        lambda **kwargs: model
    )

    monkeypatch.setattr(
        entitlement_agent,
        "execute_research_plan",
        lambda *args, **kwargs: ([], [])
    )

    monkeypatch.setattr(
        entitlement_agent,
        "add_required_clauses",
        lambda *args, **kwargs: ([], [], [])
    )

    monkeypatch.setattr(
        entitlement_agent,
        "finalize_research",
        lambda *args, **kwargs: entitlement_agent.safe_escalation(
            "Fallback retrieval requires human review."
        )
    )

    result = entitlement_agent.evaluate_entitlement(
        {"description": "My flight was cancelled."},
        {"disruption_type": "cancellation"},
        search_function=lambda query: [],
        clause_function=lambda clause_id: {}
    )

    planner.invoke.assert_not_called()

    assert result["route"] == "request-further-evidence"
    assert result["verification_passed"] is False
    assert result["human_escalation"] is True