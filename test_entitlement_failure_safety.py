
from app.agents import workflow


def test_entitlement_exception_escalates(monkeypatch):
    def failing_entitlement(*args, **kwargs):
        raise RuntimeError("Simulated Gemini or RAG failure")

    monkeypatch.setattr(
        workflow,
        "evaluate_entitlement",
        failing_entitlement
    )

    state = {
        "claim": {
            "description": "My flight was cancelled.",
            "origin": "BLR",
            "destination": "DEL"
        },
        "analysis": {
            "disruption_type": "cancellation",
            "missing_fields": [],
            "contradictions": []
        },
        "run_id": "failure-test-001"
    }

    result = workflow.entitlement_node(state)["entitlement"]

    assert result["route"] == "request-further-evidence"
    assert result["human_escalation"] is True
    assert result["verification_passed"] is False
    assert result["citation_verification"]["status"] == "not_run"
    assert result["retrieved_passages"] == []
    assert result["entitlement_review"]["verification_passed"] is False


def test_failed_entitlement_never_authorizes_payment(monkeypatch):
    def failing_entitlement(*args, **kwargs):
        raise TimeoutError("Simulated model timeout")

    monkeypatch.setattr(
        workflow,
        "evaluate_entitlement",
        failing_entitlement
    )

    state = {
        "claim": {
            "description": "My flight was cancelled.",
            "origin": "BLR",
            "destination": "DEL"
        },
        "analysis": {
            "disruption_type": "cancellation",
            "missing_fields": [],
            "contradictions": []
        }
    }

    result = workflow.entitlement_node(state)["entitlement"]

    assert result["route"] != "pay-as-computed"
    assert result["route"] != "decline"
    assert result["verification_passed"] is False
