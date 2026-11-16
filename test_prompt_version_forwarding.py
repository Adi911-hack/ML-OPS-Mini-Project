from unittest.mock import patch

import pytest

from app.agent_runner import run_agents


CLAIM = {
    "description": (
        "My flight was cancelled 90 minutes before departure."
    ),
    "origin": "BLR",
    "destination": "DEL",
    "reported_disruption": "cancellation"
}


WORKFLOW_RESULT = {
    "analysis": {
        "disruption_type": "cancellation",
        "missing_fields": [],
        "contradictions": []
    },
    "entitlement": {
        "route": "request-further-evidence",
        "reasoning": "Further evidence required.",
        "verification_passed": False,
        "entitlement_review": {
            "route": "request-further-evidence",
            "reasoning": "Further evidence required.",
            "verification_passed": False,
            "supporting_clause_ids": []
        },
        "citation_verification": {
            "status": "not_run",
            "verified_count": 0,
            "rejected_count": 0
        },
        "retrieved_passages": [],
        "tool_calls": []
    }
}


def test_basic_prompt_forwarding():
    with patch(
        "app.agent_runner.check_regulatory_scope",
        return_value={"status": "supported"}
    ), patch(
        "app.agent_runner.run_claim_agents",
        return_value=WORKFLOW_RESULT
    ) as workflow:
        result = run_agents(
            CLAIM,
            prompt_version="v1-basic"
        )

    assert result["prompt_version"] == "v1-basic"
    assert workflow.call_args.kwargs["prompt_version"] == "v1-basic"


def test_exception_aware_prompt_forwarding():
    with patch(
        "app.agent_runner.check_regulatory_scope",
        return_value={"status": "supported"}
    ), patch(
        "app.agent_runner.run_claim_agents",
        return_value=WORKFLOW_RESULT
    ) as workflow:
        result = run_agents(
            CLAIM,
            prompt_version="v2-exception-aware"
        )

    assert result["prompt_version"] == "v2-exception-aware"
    assert workflow.called


def test_default_prompt_preserved():
    with patch(
        "app.agent_runner.check_regulatory_scope",
        return_value={"status": "supported"}
    ), patch(
        "app.agent_runner.run_claim_agents",
        return_value=WORKFLOW_RESULT
    ):
        result = run_agents(CLAIM)

    assert result["prompt_version"] == "v2-exception-aware"


def test_invalid_prompt_rejected():
    with pytest.raises(ValueError):
        run_agents(
            CLAIM,
            prompt_version="invalid-version"
        )