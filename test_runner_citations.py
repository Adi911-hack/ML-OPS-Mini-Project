
from unittest.mock import patch

from app.agent_runner import run_agents


CLAIM = {
    "description": "My flight was cancelled.",
    "reported_disruption": "cancellation",
    "origin": "BLR",
    "destination": "DEL",
}


def make_result(
    status="passed",
    rejected_count=0,
    verified_count=1,
    route="request-further-evidence",
    decision_verified=False
):
    return {
        "analysis": {
            "disruption_type": "cancellation"
        },
        "entitlement": {
            "route": route,
            "verification_passed": decision_verified,
            "retrieved_passages": [
                {
                    "document": "DGCA",
                    "clause_id": "DGCA:3.3.2",
                    "page": 2,
                    "passage": "Verified test passage"
                }
            ],
            "citation_verification": {
                "status": status,
                "verified_count": verified_count,
                "rejected_count": rejected_count
            },
            "entitlement_review": {
                "route": route,
                "reasoning": "Further review is required.",
                "supporting_clause_ids": ["DGCA:3.3.2"],
                "verification_passed": decision_verified
            }
        }
    }


def test_verified_citations_are_returned():
    with patch(
        "app.agent_runner.run_claim_agents",
        return_value=make_result()
    ):
        result = run_agents(CLAIM)

    assert len(result["citations"]) == 1
    assert result["citations"][0]["clause_id"] == "DGCA:3.3.2"
    assert result["citations"][0]["text"] == "Verified test passage"
    assert result["verified"] is False
    assert result["route"] == "request-further-evidence"


def test_failed_citation_check_blocks_citations():
    with patch(
        "app.agent_runner.run_claim_agents",
        return_value=make_result(
            status="failed",
            rejected_count=1,
            verified_count=0
        )
    ):
        result = run_agents(CLAIM)

    assert result["citations"] == []
    assert result["verified"] is False


def test_unverified_compensation_is_blocked():
    with patch(
        "app.agent_runner.run_claim_agents",
        return_value=make_result(
            route="pay-as-computed",
            decision_verified=False
        )
    ):
        result = run_agents(CLAIM)

    assert result["route"] == "request-further-evidence"
    assert result["outcome"] == "escalated"
    assert result["verified"] is False


def test_verified_route_can_be_forwarded():
    with patch(
        "app.agent_runner.run_claim_agents",
        return_value=make_result(
            route="decline",
            decision_verified=True
        )
    ):
        result = run_agents(CLAIM)

    assert result["route"] == "decline"
    assert result["outcome"] == "routed"
    assert result["verified"] is True
