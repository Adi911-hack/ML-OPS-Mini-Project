
from app.agents.entitlement_agent import (
    fallback_plan,
    execute_research_plan,
    add_required_clauses
)
from app.agents.rag_adapter import (
    search_documents,
    lookup_clause
)


claim = {
    "airline": "IndiGo",
    "disruption_type": "cancellation",
    "notice_minutes": 90,
    "block_time_minutes": None,
    "alternate_flight_offered": True,
    "alternate_flight_accepted": True,
    "contact_details_provided": None
}

plan = fallback_plan("cancellation")

calls, evidence = execute_research_plan(
    plan,
    claim,
    search_documents,
    lookup_clause
)

evidence, calls, missing = add_required_clauses(
    "cancellation",
    evidence,
    calls,
    lookup_clause
)

clause_ids = {
    item["clause_id"]
    for item in evidence
}

required = {
    "DGCA:3.3.1",
    "DGCA:3.3.2",
    "DGCA:3.3.3",
    "DGCA:3.3.4",
    "DGCA:3.8.1"
}

assert not missing, f"Missing clauses: {missing}"
assert required.issubset(clause_ids)

print("Fallback retrieval test PASSED")
print("Retrieved passages:", len(evidence))
print("Required clauses:", sorted(required))
