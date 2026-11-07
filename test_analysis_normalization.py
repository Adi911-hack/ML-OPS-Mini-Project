
from app.agents.workflow import normalize_claim_analysis


claim = {
    "airline": "IndiGo",
    "notice_minutes": 90,
    "block_time_minutes": None,
    "alternate_flight_offered": True,
    "alternate_flight_accepted": True,
    "contact_details_provided": None
}

raw_analysis = {
    "disruption_type": "cancellation",
    "airline": "IndiGo",
    "notice_minutes": None,
    "block_time_minutes": None,
    "alternate_flight_offered": True,
    "alternate_flight_accepted": True,
    "contact_details_provided": None,
    "missing_fields": [],
    "contradictions": [],
    "explanation": "Cancellation identified."
}

result = normalize_claim_analysis(claim, raw_analysis)

assert result["disruption_type"] == "cancellation"
assert result["notice_minutes"] == 90
assert result["block_time_minutes"] is None
assert result["contact_details_provided"] is None
assert "block_time_minutes" in result["missing_fields"]
assert "contact_details_provided" in result["missing_fields"]
assert "notice_minutes" not in result["missing_fields"]

print("Agent 1 normalization test PASSED")
print("Notice minutes:", result["notice_minutes"])
print("Missing fields:", result["missing_fields"])
