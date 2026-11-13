
from unittest.mock import Mock

from app.agents import claim_analyst


def sample_claim():
    return {
        "airline": "IndiGo",
        "disruption_type": "cancellation",
        "notice_minutes": 90,
        "block_time_minutes": 150,
        "alternate_flight_offered": True,
        "alternate_flight_accepted": True,
        "contact_details_provided": True,
        "claim_description": "My flight was cancelled."
    }


def test_temporary_error_detection():
    error = Exception(
        "503 UNAVAILABLE: model is currently experiencing high demand"
    )

    assert claim_analyst.is_temporary_model_error(error)
    assert not claim_analyst.is_temporary_model_error(
        Exception("400 INVALID_ARGUMENT")
    )


def test_fallback_does_not_authorize_compensation():
    claim = claim_analyst.PassengerClaim.model_validate(
        sample_claim()
    )

    result = claim_analyst.fallback_analysis(claim)

    assert result["disruption_type"] == "unknown"
    assert result["airline"] == "IndiGo"
    assert result["notice_minutes"] == 90
    assert result["contact_details_provided"] is True
    assert "claim_analysis_unavailable" in result["missing_fields"]
    assert "Human review" in result["explanation"]


def test_retries_then_returns_safe_fallback(monkeypatch):
    monkeypatch.setenv("MODEL_NAME", "test-model")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

    monkeypatch.setattr(
        claim_analyst,
        "ChatGoogleGenerativeAI",
        lambda **kwargs: object()
    )

    monkeypatch.setattr(
        claim_analyst,
        "create_claim_tools",
        lambda claim: []
    )

    agent = Mock()
    agent.invoke.side_effect = Exception(
        "503 UNAVAILABLE: high demand"
    )

    monkeypatch.setattr(
        claim_analyst,
        "create_agent",
        lambda **kwargs: agent
    )

    monkeypatch.setattr(
        claim_analyst.time,
        "sleep",
        lambda seconds: None
    )

    result = claim_analyst.analyze_claim(sample_claim())

    assert agent.invoke.call_count == 3
    assert result["disruption_type"] == "unknown"
    assert "claim_analysis_unavailable" in result["missing_fields"]


def test_non_retryable_error_is_raised(monkeypatch):
    monkeypatch.setenv("MODEL_NAME", "test-model")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

    monkeypatch.setattr(
        claim_analyst,
        "ChatGoogleGenerativeAI",
        lambda **kwargs: object()
    )

    monkeypatch.setattr(
        claim_analyst,
        "create_claim_tools",
        lambda claim: []
    )

    agent = Mock()
    agent.invoke.side_effect = ValueError("Invalid request")

    monkeypatch.setattr(
        claim_analyst,
        "create_agent",
        lambda **kwargs: agent
    )

    try:
        claim_analyst.analyze_claim(sample_claim())
    except ValueError as error:
        assert str(error) == "Invalid request"
    else:
        raise AssertionError("Expected ValueError")
