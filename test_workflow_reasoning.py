
from app.agents.workflow import attach_entitlement_review
from app.agents.rag_adapter import lookup_clause
from app.agents.citation_verifier import verify_passages


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

claim = {
    "airline": "IndiGo",
    "notice_minutes": 90,
    "alternate_flight_offered": True,
    "alternate_flight_accepted": True
}

analysis = {
    "disruption_type": "cancellation",
    "notice_minutes": 90,
    "block_time_minutes": None,
    "alternate_flight_offered": True,
    "alternate_flight_accepted": True,
    "contact_details_provided": None
}

entitlement = {
    "route": "request-further-evidence",
    "recommendation": "Human review required",
    "human_escalation": True,
    "verification_passed": False,
    "retrieved_passages": verification["verified_passages"],
    "citation_verification": {
        "status": verification["status"],
        "verified_count": verification["verified_count"],
        "rejected_count": verification["rejected_count"]
    }
}

result = attach_entitlement_review(
    claim,
    analysis,
    entitlement
)

review = result["entitlement_review"]

assert review["route"] == "request-further-evidence"
assert review["verification_passed"] is False
assert len(review["supporting_clause_ids"]) == 5
assert "block_time_minutes" in review["missing_information"]
assert "contact_details_provided" in review["missing_information"]

print("Workflow entitlement reasoning integration PASSED")

invalid_entitlement = dict(entitlement)
invalid_entitlement["citation_verification"] = {
    "status": "failed",
    "verified_count": 0,
    "rejected_count": 1
}

invalid_result = attach_entitlement_review(
    claim,
    analysis,
    invalid_entitlement
)

invalid_review = invalid_result["entitlement_review"]

assert invalid_review["conditions"] == []
assert invalid_review["supporting_clause_ids"] == []
assert "verified_regulatory_evidence" in invalid_review["missing_information"]
assert invalid_result["verification_passed"] is False

print("Failed citation verification blocks reasoning PASSED")
print("All workflow reasoning tests PASSED")
