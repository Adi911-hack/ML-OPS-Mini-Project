
from app.agents.entitlement_agent import finalize_research
from app.agents.rag_adapter import lookup_clause


valid = lookup_clause("DGCA:3.3.2")

assert valid["status"] == "ok"

result = finalize_research(
    evidence=[valid["clause"]],
    tool_calls=[],
    clause_function=lookup_clause
)

assert result["citation_verification"]["status"] == "passed"
assert result["citation_verification"]["verified_count"] == 1
assert result["citation_verification"]["rejected_count"] == 0
assert result["verification_passed"] is False
assert len(result["retrieved_passages"]) == 1

print("Agent 2 valid citation integration PASSED")


fake = dict(valid["clause"])
fake["passage"] = "Every passenger must receive INR 50000."

result = finalize_research(
    evidence=[fake],
    tool_calls=[],
    clause_function=lookup_clause
)

assert result["citation_verification"]["status"] == "failed"
assert result["citation_verification"]["rejected_count"] == 1
assert result["verification_passed"] is False
assert result["retrieved_passages"] == []
assert result["human_escalation"] is True

print("Agent 2 fabricated citation rejection PASSED")
print("All Agent 2 citation integration tests PASSED")
