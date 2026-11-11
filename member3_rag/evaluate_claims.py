
from pathlib import Path
import json
import argparse
from member3_rag.rag_interface import search_corpus, get_clause_by_id

BASE_DIR = Path(__file__).resolve().parent
CASES_FILE = BASE_DIR / "claim_evaluation_cases.json"
RESULTS_FILE = BASE_DIR / "claim_evaluation_results.json"


def evaluate(top_k=5):
    if top_k < 1:
        raise ValueError("top_k must be positive")

    with open(CASES_FILE, "r", encoding="utf-8") as file:
        cases = json.load(file)

    if not cases:
        raise ValueError("No evaluation scenarios found")

    reports = []
    expected_total = 0
    found_total = 0
    reciprocal_rank_total = 0
    cases_with_all_clauses = 0
    missing_references = set()
    evaluated_cases = 0

    for case in cases:
        expected = case["expected_clauses"]
        found = []
        missing = []

        for clause_id in expected:
            clause = get_clause_by_id(clause_id)

            if clause is None:
                missing.append(clause_id)
                missing_references.add(clause_id)

        results = search_corpus(case["claim"], top_k=top_k)

        retrieved_ids = [
            item["clause_id"] for item in results
        ]

        ranks = {}

        for clause_id in expected:
            if clause_id in retrieved_ids:
                rank = retrieved_ids.index(clause_id) + 1
                found.append(clause_id)
                ranks[clause_id] = rank
                reciprocal_rank_total += 1 / rank

        expected_total += len(expected)
        found_total += len(found)

        if expected:
            evaluated_cases += 1

            if len(found) == len(expected):
                cases_with_all_clauses += 1

        report = {
            "id": case["id"],
            "category": case["category"],
            "claim": case["claim"],
            "expected_clauses": expected,
            "retrieved_clauses": retrieved_ids,
            "found_clauses": found,
            "missing_references": missing,
            "ranks": ranks,
            "all_expected_found": (
                len(found) == len(expected)
                if expected else None
            ),
            "expected_outcome": case["expected_outcome"],
            "expected_route": case["expected_route"]
        }

        reports.append(report)

        if not expected:
            status = "NOT SCORED"
        elif len(found) == len(expected):
            status = "PASS"
        else:
            status = "FAIL"

        print(f"\n{case['id']} | {case['category']} | {status}")
        print(f"Expected: {expected}")
        print(f"Retrieved: {retrieved_ids}")
        print(f"Found: {found}")

        if missing:
            print(f"Missing from database: {missing}")

    recall = found_total / expected_total if expected_total else 0

    case_success = (
        cases_with_all_clauses / evaluated_cases
        if evaluated_cases else 0
    )

    mean_reciprocal = (
        reciprocal_rank_total / expected_total
        if expected_total else 0
    )

    summary = {
        "total_scenarios": len(cases),
        "scenarios_with_expected_clauses": evaluated_cases,
        "expected_clause_references": expected_total,
        "retrieved_clause_references": found_total,
        "clause_recall_at_k": round(recall, 4),
        "all_clauses_hit_rate": round(case_success, 4),
        "mean_reciprocal_rank_per_clause": round(mean_reciprocal, 4),
        "missing_reference_ids": sorted(missing_references),
        "top_k": top_k,
        "results": reports
    }

    with open(RESULTS_FILE, "w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2, ensure_ascii=False)

    print("\n" + "=" * 45)
    print("RAG EVALUATION SUMMARY")
    print("=" * 45)
    print(f"Total scenarios: {len(cases)}")
    print(f"Scored scenarios: {evaluated_cases}")
    print(f"Expected clause references: {expected_total}")
    print(f"Retrieved clause references: {found_total}")
    print(f"Clause Recall@{top_k}: {recall:.2%}")
    print(f"All-clauses hit rate: {case_success:.2%}")
    print(f"Mean reciprocal rank per clause: {mean_reciprocal:.4f}")
    print(f"Missing reference IDs: {sorted(missing_references)}")
    print(f"Results saved to: {RESULTS_FILE}")

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    evaluate(args.top_k)
