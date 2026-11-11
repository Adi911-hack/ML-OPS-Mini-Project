
from app.agents.entitlement_reasoner import review_entitlement
from app.agents.citation_verifier import verify_passages
from app.agents.rag_adapter import lookup_clause


required = [
    "DGCA:3.3.1",
    "DGCA:3.3.2",
    "DGCA:3.3.3",
    "DGCA:3.3.4",
    "DGCA:3.8.1"
]

passages = []

for clause_id in required:
    response = lookup_clause(clause_id)
    assert response["status"] == "ok"
    passages.append(response["clause"])

verification = verify_passages(passages, lookup_clause)

assert verification["status"] == "passed"
assert verification["verified_count"] == 5

claim = {
    "airline": "IndiGo",
    "claim_description": (
        "My flight was cancelled 90 minutes before "
        "departure and I accepted an alternate flight."
    )
}

analysis = {
    "disruption_type": "cancellation",
    "notice_minutes": 90,
    "block_time_minutes": None,
    "alternate_flight_offered": True,
    "alternate_flight_accepted": True,
    "contact_details_provided": None
}

result = review_entitlement(
    claim,
    analysis,
    verification["verified_passages"]
)

assert result["route"] == "request-further-evidence"
assert result["human_escalation"] is True
assert result["verification_passed"] is False
assert len(result["supporting_clause_ids"]) == 5

assert "block_time_minutes" in result["missing_information"]
assert "contact_details_provided" in result["missing_information"]

conditions = {
    item["name"]: item
    for item in result["conditions"]
}

assert conditions["cancellation_notice"]["value_minutes"] == 90
assert conditions["alternate_flight"]["status"] == "accepted"
assert conditions["flight_block_time"]["status"] == "unknown"
assert conditions["contact_information"]["status"] == "unknown"

print("Cancellation entitlement reasoning test PASSED")
print("Missing information:", result["missing_information"])
print("Route:", result["route"])

incomplete = review_entitlement(
    claim,
    analysis,
    verification["verified_passages"][:1]
)

assert incomplete["verification_passed"] is False
assert incomplete["human_escalation"] is True
assert incomplete["supporting_clause_ids"] == []

print("Missing regulatory evidence test PASSED")
print("All entitlement reasoning tests PASSED")
