
from unittest.mock import patch

from app.agent_runner import run_agents
from app.agents.workflow import attach_entitlement_review


CLAIM = {
    "description": "My flight was cancelled.",
    "reported_disruption": "cancellation",
    "airline": "IndiGo",
    "origin": "BLR",
    "destination": "DEL"
}


def test_compensation_details_reach_api_result():
    monetary = {
        "status": "potentially_payable",
        "amount_inr": None,
        "maximum_cap_inr": 10000
    }

    assistance = {
        "status": "needs_evidence",
        "meals_and_refreshments": "potentially_applicable",
        "hotel_accommodation": "subject_to_necessity"
    }

    workflow_result = {
        "analysis": {
            "disruption_type": "cancellation"
        },
        "entitlement": {
            "route": "request-further-evidence",
            "verification_passed": False,
            "entitlement_review": {
                "route": "request-further-evidence",
                "reasoning": "Additional evidence required.",
                "verification_passed": False
            },
            "monetary_compensation": monetary,
            "airport_assistance": assistance,
            "retrieved_passages": [],
            "citation_verification": {
                "status": "not_run",
                "verified_count": 0,
                "rejected_count": 0
            },
            "tool_calls": []
        }
    }

    with patch(
        "app.agent_runner.run_claim_agents",
        return_value=workflow_result
    ):
        result = run_agents(CLAIM)

    assert result["monetary_compensation"] == monetary
    assert result["airport_assistance"] == assistance
    assert result["route"] == "request-further-evidence"
    assert result["outcome"] == "escalated"
    assert result["verified"] is False


def test_workflow_preserves_reasoner_details(monkeypatch):
    monetary = {
        "status": "alternate_flight_accepted",
        "amount_inr": None,
        "maximum_cap_inr": 7500
    }

    assistance = {
        "status": "needs_evidence",
        "meals_and_refreshments": "potentially_applicable",
        "hotel_accommodation": "subject_to_necessity"
    }

    def fake_review(claim, analysis, passages):
        return {
            "route": "request-further-evidence",
            "reasoning": "Assistance needs confirmation.",
            "supporting_clause_ids": ["DGCA:3.3.2"],
            "human_escalation": True,
            "verification_passed": False,
            "monetary_compensation": monetary,
            "airport_assistance": assistance
        }

    monkeypatch.setattr(
        "app.agents.workflow.review_entitlement",
        fake_review
    )

    entitlement = {
        "retrieved_passages": [
            {
                "clause_id": "DGCA:3.3.2",
                "document": "DGCA",
                "page": 5,
                "passage": "Test passage."
            }
        ],
        "citation_verification": {
            "status": "passed",
            "verified_count": 1,
            "rejected_count": 0
        }
    }

    result = attach_entitlement_review(
        CLAIM,
        {"disruption_type": "cancellation"},
        entitlement
    )

    assert result["monetary_compensation"] == monetary
    assert result["airport_assistance"] == assistance
    assert result["route"] == "request-further-evidence"
    assert result["verification_passed"] is False
