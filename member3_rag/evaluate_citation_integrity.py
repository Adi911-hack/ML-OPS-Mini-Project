from pathlib import Path
import json

from member3_rag.rag_interface import search_corpus, get_clause_by_id

BASE_DIR = Path(__file__).resolve().parent
CASES_FILE = BASE_DIR / "claim_evaluation_cases.json"
RESULTS_FILE = BASE_DIR / "citation_integrity_results.json"


def check_passage(passage):
    clause = get_clause_by_id(passage["clause_id"])

    if clause is None:
        return False

    return (
        passage["source"] == clause["source"]
        and passage["page"] == clause["page"]
        and passage["text"] == clause["text"]
    )


def evaluate():
    with open(CASES_FILE, "r", encoding="utf-8") as file:
        cases = json.load(file)

    total_passages = 0
    verified_passages = 0
    rejected_passages = 0
    tampering_tests = 0
    tampering_rejected = 0
    reports = []

    for case in cases:
        passages = search_corpus(case["claim"], top_k=5)

        verified = 0
        rejected = 0

        for passage in passages:
            if check_passage(passage):
                verified += 1
            else:
                rejected += 1

        total_passages += len(passages)
        verified_passages += verified
        rejected_passages += rejected

        tampering_detected = None

        if passages:
            tampered = dict(passages[0])
            tampered["text"] = "The airline must pay INR 50000."

            tampering_detected = not check_passage(tampered)

            tampering_tests += 1

            if tampering_detected:
                tampering_rejected += 1

        reports.append({
            "id": case["id"],
            "retrieved": len(passages),
            "verified": verified,
            "rejected": rejected,
            "tampering_detected": tampering_detected
        })

        print(
            f"{case['id']} | "
            f"Verified: {verified}/{len(passages)} | "
            f"Tampering rejected: {tampering_detected}"
        )

    integrity_rate = (
        verified_passages / total_passages
        if total_passages else 0
    )

    tampering_rejection_rate = (
        tampering_rejected / tampering_tests
        if tampering_tests else 0
    )

    summary = {
        "total_scenarios": len(cases),
        "total_passages": total_passages,
        "verified_passages": verified_passages,
        "rejected_passages": rejected_passages,
        "citation_integrity_rate": round(integrity_rate, 4),
        "tampering_tests": tampering_tests,
        "tampering_rejected": tampering_rejected,
        "tampering_rejection_rate": round(tampering_rejection_rate, 4),
        "results": reports
    }

    with open(RESULTS_FILE, "w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2)

    print("\n" + "=" * 45)
    print("CITATION INTEGRITY SUMMARY")
    print("=" * 45)
    print(f"Total scenarios: {len(cases)}")
    print(f"Retrieved passages: {total_passages}")
    print(f"Verified passages: {verified_passages}")
    print(f"Rejected passages: {rejected_passages}")
    print(f"Citation integrity: {integrity_rate:.2%}")
    print(f"Tampering rejection: {tampering_rejection_rate:.2%}")
    print(f"Results saved to: {RESULTS_FILE}")

    return summary


if __name__ == "__main__":
    evaluate()