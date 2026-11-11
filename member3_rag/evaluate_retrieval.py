
from pathlib import Path
import json
import re
from retriever import search_regulations

BASE_DIR = Path(__file__).resolve().parent
CASES_FILE = BASE_DIR / "evaluation_cases.json"
RESULTS_FILE = BASE_DIR / "evaluation_results.json"


def clause_found(text, clause):
    pattern = rf"(?<![\d.]){re.escape(clause)}(?![\d.])"
    return re.search(pattern, text) is not None


def evaluate(top_k=5):
    with open(CASES_FILE, "r", encoding="utf-8") as file:
        cases = json.load(file)

    results = []
    hits = 0
    reciprocal_rank_sum = 0

    for case in cases:
        matches = search_regulations(case["question"], top_k)
        correct_rank = None

        for rank, match in enumerate(matches, start=1):
            if (
                match["source"] == case["expected_source"]
                and clause_found(match["text"], case["expected_clause"])
            ):
                correct_rank = rank
                break

        passed = correct_rank is not None

        if passed:
            hits += 1
            reciprocal_rank_sum += 1 / correct_rank

        results.append({
            "id": case["id"],
            "category": case["category"],
            "question": case["question"],
            "expected_source": case["expected_source"],
            "expected_clause": case["expected_clause"],
            "passed": passed,
            "rank": correct_rank
        })

        status = "PASS" if passed else "FAIL"
        print(f"{case['id']} | {case['category']} | {status}")
        print(f"Expected clause: {case['expected_clause']}")
        print(f"Rank: {correct_rank if passed else 'Not found'}")
        print()

    total = len(cases)
    recall = hits / total if total else 0
    mrr = reciprocal_rank_sum / total if total else 0

    report = {
        "total_cases": total,
        "passed": hits,
        "failed": total - hits,
        "recall_at_k": recall,
        "mrr_at_k": mrr,
        "top_k": top_k,
        "results": results
    }

    with open(RESULTS_FILE, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    print(f"Total cases: {total}")
    print(f"Passed: {hits}")
    print(f"Failed: {total - hits}")
    print(f"Recall@{top_k}: {recall:.2%}")
    print(f"MRR@{top_k}: {mrr:.4f}")
    print(f"Results saved to: {RESULTS_FILE}")

    return report


if __name__ == "__main__":
    evaluate()
