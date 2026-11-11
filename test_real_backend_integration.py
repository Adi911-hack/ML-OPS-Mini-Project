
import json

from app.agent_runner import run_agents


claim = {
    "passenger_name": "Test Passenger",
    "booking_reference": "ABC123",
    "airline": "IndiGo",
    "flight_number": "6E123",
    "origin": "BLR",
    "destination": "DEL",
    "scheduled_departure": "2026-11-15T10:00:00+05:30",
    "description": (
        "My flight was cancelled 90 minutes before "
        "departure. The airline offered another flight "
        "four hours later and I accepted it."
    ),
    "reported_disruption": "cancellation",
    "notice_minutes": 90,
    "block_time_minutes": None,
    "alternate_flight_offered": True,
    "alternate_flight_accepted": True,
    "contact_details_provided": None
}

try:
    result = run_agents(claim)

    assert result["outcome"] == "escalated"
    assert result["route"] == "request-further-evidence"
    assert result["verified"] is False
    assert result["analysis"]["disruption_type"] == "cancellation"
    assert result["analysis"]["notice_minutes"] == 90
    assert result["citation_verification"]["status"] == "passed"
    assert result["citation_verification"]["rejected_count"] == 0
    assert result["citation_verification"]["verified_count"] >= 5

    review = result["entitlement_review"]

    assert review["human_escalation"] is True
    assert review["verification_passed"] is False
    assert "block_time_minutes" in review["missing_information"]
    assert "contact_details_provided" in review["missing_information"]

    print()
    print("REAL BACKEND INTEGRATION TEST PASSED")
    print()
    print("Outcome:", result["outcome"])
    print("Route:", result["route"])
    print("Verified:", result["verified"])
    print("Matched citations:", result["citation_verification"]["verified_count"])
    print("Missing information:", review["missing_information"])

except Exception as error:
    print()
    print("REAL BACKEND INTEGRATION TEST FAILED")
    print(type(error).__name__, str(error))
    raise
