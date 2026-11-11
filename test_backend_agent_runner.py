
from unittest.mock import patch

from app.agent_runner import prepare_agent_claim, run_agents


claim = {
    "passenger_name": "Test Passenger",
    "booking_reference": "ABC123",
    "airline": "IndiGo",
    "flight_number": "6E123",
    "origin": "BLR",
    "destination": "DEL",
    "scheduled_departure": "2026-11-15T10:00:00+05:30",
    "description": (
        "My flight was cancelled 90 minutes before departure."
    ),
    "reported_disruption": "cancellation",
    "notice_minutes": 90,
    "block_time_minutes": None,
    "alternate_flight_offered": True,
    "alternate_flight_accepted": True,
    "contact_details_provided": None
}

prepared = prepare_agent_claim(claim)

assert prepared["claim_description"] == claim["description"]
assert prepared["disruption_type"] == "cancellation"
assert prepared["airline"] == "IndiGo"
assert claim.get("claim_description") is None

print("Backend claim field mapping PASSED")


fake_workflow_result = {
    "status": "completed",
    "analysis": {
        "disruption_type": "cancellation",
        "notice_minutes": 90
    },
    "entitlement": {
        "route": "request-further-evidence",
        "reasoning": "Further evidence is required.",
        "escalation_reason": "Missing supporting information.",
        "human_escalation": True,
        "verification_passed": False,
        "tool_calls": [],
        "citation_verification": {
            "status": "passed",
            "verified_count": 5,
            "rejected_count": 0
        },
        "entitlement_review": {
            "route": "request-further-evidence",
            "reasoning": "Some claim conditions are unknown."
        }
    }
}

with patch(
    "app.agent_runner.run_claim_agents",
    return_value=fake_workflow_result
) as mock_workflow:
    result = run_agents(claim)

    mock_workflow.assert_called_once()

assert result["outcome"] == "escalated"
assert result["route"] == "request-further-evidence"
assert result["verified"] is False
assert result["citations"] == []
assert result["analysis"]["disruption_type"] == "cancellation"
assert result["entitlement_review"]

print("Backend agent response mapping PASSED")
print("All backend agent runner tests PASSED")
