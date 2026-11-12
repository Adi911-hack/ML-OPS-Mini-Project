
from app.agents import workflow


def test_analyst_fallback_skips_entitlement(monkeypatch):
    def unexpected_entitlement(*args, **kwargs):
        raise AssertionError(
            "Entitlement Agent must not run after analyst fallback"
        )

    monkeypatch.setattr(
        workflow,
        "evaluate_entitlement",
        unexpected_entitlement
    )

    state = {
        "claim": {
            "origin": "BLR",
            "destination": "DEL",
            "description": "My flight was cancelled."
        },
        "analysis": {
            "disruption_type": "unknown",
            "missing_fields": [
                "claim_analysis_unavailable"
            ],
            "contradictions": [],
            "explanation": "Claim Analyst unavailable."
        },
        "run_id": "fallback-test-001"
    }

    result = workflow.entitlement_node(state)
    entitlement = result["entitlement"]

    assert entitlement["route"] == "request-further-evidence"
    assert entitlement["human_escalation"] is True
    assert entitlement["verification_passed"] is False
    assert entitlement["retrieved_passages"] == []
    assert entitlement["tool_calls"] == []
    assert entitlement["citation_verification"]["status"] == "not_run"
    assert (
        entitlement["entitlement_review"]["verification_passed"]
        is False
    )
