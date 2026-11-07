
def verify_passages(passages, clause_function):
    verified = []
    rejected = []
    cache = {}

    if not isinstance(passages, list):
        raise ValueError("Passages must be a list")

    for passage in passages:
        if not isinstance(passage, dict):
            rejected.append({
                "passage": passage,
                "reason": "Invalid passage format"
            })
            continue

        clause_id = passage.get("clause_id")

        if not clause_id:
            rejected.append({
                "passage": passage,
                "reason": "Missing clause ID"
            })
            continue

        if clause_id not in cache:
            try:
                cache[clause_id] = clause_function(clause_id)
            except Exception:
                cache[clause_id] = {
                    "status": "unavailable",
                    "clause": None
                }

        result = cache[clause_id]

        if not isinstance(result, dict):
            rejected.append({
                "passage": passage,
                "reason": "Invalid lookup response"
            })
            continue

        if result.get("status") != "ok":
            rejected.append({
                "passage": passage,
                "reason": "Clause not found or unavailable"
            })
            continue

        original = result.get("clause")

        if not isinstance(original, dict):
            rejected.append({
                "passage": passage,
                "reason": "Original clause is missing"
            })
            continue

        fields = [
            "clause_id",
            "document",
            "page",
            "passage"
        ]

        if any(
            passage.get(field) != original.get(field)
            for field in fields
        ):
            rejected.append({
                "passage": passage,
                "reason": "Citation does not match indexed clause"
            })
            continue

        verified.append({
            "clause_id": original["clause_id"],
            "document": original["document"],
            "page": original["page"],
            "passage": original["passage"]
        })

    return {
        "status": "passed" if not rejected else "failed",
        "verified_count": len(verified),
        "rejected_count": len(rejected),
        "verified_passages": verified,
        "rejected_passages": rejected
    }
