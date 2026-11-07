
from app.agents.citation_verifier import verify_passages
from app.agents.rag_adapter import lookup_clause


clause_ids = [
    "DGCA:3.3.2",
    "DGCA:3.3.3",
    "DGCA:3.8.1"
]

passages = []

for clause_id in clause_ids:
    result = lookup_clause(clause_id)
    assert result["status"] == "ok"
    passages.append(result["clause"])

result = verify_passages(passages, lookup_clause)

assert result["status"] == "passed"
assert result["verified_count"] == 3
assert result["rejected_count"] == 0

print("Valid citation verification PASSED")

fake_passage = dict(passages[0])
fake_passage["passage"] = "The airline must pay INR 50000."

fake_result = verify_passages(
    [fake_passage],
    lookup_clause
)

assert fake_result["status"] == "failed"
assert fake_result["verified_count"] == 0
assert fake_result["rejected_count"] == 1

print("Fabricated citation rejection PASSED")

nonexistent = {
    "clause_id": "DGCA:999.999",
    "document": "fake.pdf",
    "page": 1,
    "passage": "Fake regulation"
}

missing_result = verify_passages(
    [nonexistent],
    lookup_clause
)

assert missing_result["status"] == "failed"
assert missing_result["rejected_count"] == 1

print("Nonexistent clause rejection PASSED")
print("All citation verifier tests PASSED")
