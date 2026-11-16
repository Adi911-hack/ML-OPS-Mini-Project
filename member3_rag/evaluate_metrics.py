import argparse
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "agent_evaluation_results"

VERSIONS = ["v1-basic", "v2-exception-aware"]


def read_json(path):
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def get_response_text(result):
    parts = [
        result.get("agent_recommendation"),
        result.get("agent_reasoning")
    ]

    return "\n".join(
        str(part) for part in parts if part
    )


def prepare_reviews(version):
    results_file = RESULTS_DIR / f"{version}.json"
    review_file = RESULTS_DIR / f"{version}_reviews.json"

    results = read_json(results_file)

    existing = {}

    if review_file.exists():
        existing = read_json(review_file)

    reviews = {}

    for scenario_id, result in results.items():
        if result.get("status") != "completed":
            continue

        if scenario_id in existing:
            reviews[scenario_id] = existing[scenario_id]
            continue

        passages = result.get("retrieved_passages") or []

        reviews[scenario_id] = {
            "scenario_id": scenario_id,
            "prompt_version": version,
            "claim": result.get("claim", ""),
            "expected_outcome": result.get(
                "expected_outcome", ""
            ),
            "expected_clauses": result.get(
                "expected_clauses", []
            ),
            "agent_response": get_response_text(result),
            "retrieved_clause_ids": [
                passage.get("clause_id")
                for passage in passages
            ],
            "relevant_clause_ids": None,
            "factual_claims": [],
            "review_complete": False
        }

    save_json(review_file, reviews)

    print(f"Review file created: {review_file}")
    print(f"Scenarios: {len(reviews)}")


def validate_review(review):
    if review.get("review_complete") is not True:
        return False

    relevant = review.get("relevant_clause_ids")

    if not isinstance(relevant, list):
        return False

    retrieved = set(
        review.get("retrieved_clause_ids") or []
    )

    if any(clause not in retrieved for clause in relevant):
        return False

    claims = review.get("factual_claims")

    if not isinstance(claims, list):
        return False

    response = review.get("agent_response", "")

    if response.strip() and not claims:
        return False

    for claim in claims:
        if not isinstance(claim, dict):
            return False

        if not isinstance(claim.get("text"), str):
            return False

        if not claim["text"].strip():
            return False

        if type(claim.get("supported")) is not bool:
            return False

        if type(claim.get("faithful")) is not bool:
            return False

        if claim["faithful"] and not claim["supported"]:
            return False

    return True


def score_review(review):
    passages = review.get("retrieved_clause_ids") or []
    relevant = review["relevant_clause_ids"]
    claims = review["factual_claims"]

    unique_passages = set(passages)
    unique_relevant = set(relevant)

    context_relevance = (
        len(unique_relevant) / len(unique_passages)
        if unique_passages else None
    )

    total_claims = len(claims)

    supported = sum(
        claim["supported"] for claim in claims
    )

    faithful = sum(
        claim["faithful"] for claim in claims
    )

    hallucinated = total_claims - supported

    groundedness = (
        supported / total_claims
        if total_claims else None
    )

    faithfulness = (
        faithful / total_claims
        if total_claims else None
    )

    hallucination_rate = (
        hallucinated / total_claims
        if total_claims else None
    )

    return {
        "scenario_id": review["scenario_id"],
        "prompt_version": review["prompt_version"],
        "context_relevance": context_relevance,
        "groundedness": groundedness,
        "faithfulness": faithfulness,
        "hallucination_rate": hallucination_rate,
        "total_factual_claims": total_claims,
        "supported_claims": supported,
        "faithful_claims": faithful,
        "unsupported_claims": hallucinated
    }


def average(values):
    valid = [
        value for value in values
        if value is not None
    ]

    if not valid:
        return None

    return round(sum(valid) / len(valid), 4)


def score_version(version):
    review_file = RESULTS_DIR / f"{version}_reviews.json"

    reviews = read_json(review_file)

    scores = []
    incomplete = []

    for scenario_id, review in reviews.items():
        if not validate_review(review):
            incomplete.append(scenario_id)
            continue

        scores.append(score_review(review))

    metrics = [
        "groundedness",
        "context_relevance",
        "faithfulness",
        "hallucination_rate"
    ]

    summary = {
        "prompt_version": version,
        "total_scenarios": len(reviews),
        "scored_scenarios": len(scores),
        "incomplete_scenarios": incomplete,
        "metrics": {},
        "results": scores
    }

    for metric in metrics:
        summary["metrics"][metric] = average([
            score.get(metric) for score in scores
        ])

    output_file = RESULTS_DIR / f"{version}_metrics.json"

    save_json(output_file, summary)

    print(f"\nPROMPT VERSION: {version}")
    print("=" * 45)
    print(f"Scored scenarios: {len(scores)}/{len(reviews)}")

    for metric, value in summary["metrics"].items():
        if value is None:
            print(f"{metric}: N/A")
        else:
            print(f"{metric}: {value:.2%}")

    if incomplete:
        print(f"Incomplete reviews: {incomplete}")

    print(f"Saved to: {output_file}")

    return summary


def compare_versions():
    first = score_version(VERSIONS[0])
    second = score_version(VERSIONS[1])

    metrics = [
        "groundedness",
        "context_relevance",
        "faithfulness",
        "hallucination_rate"
    ]

    comparison = {
        "before": VERSIONS[0],
        "after": VERSIONS[1],
        "metrics": {}
    }

    print("\nBEFORE VS AFTER")
    print("=" * 45)

    for metric in metrics:
        before = first["metrics"][metric]
        after = second["metrics"][metric]

        if before is None or after is None:
            comparison["metrics"][metric] = None
            print(f"{metric}: N/A")
            continue

        difference = round(after - before, 4)

        comparison["metrics"][metric] = {
            "before": before,
            "after": after,
            "difference": difference
        }

        print(
            f"{metric}: "
            f"{before:.2%} -> {after:.2%} "
            f"({difference:+.2%})"
        )

    output_file = RESULTS_DIR / "prompt_comparison.json"

    save_json(output_file, comparison)

    print(f"\nSaved to: {output_file}")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--prepare",
        choices=VERSIONS
    )

    parser.add_argument(
        "--score",
        choices=VERSIONS
    )

    parser.add_argument(
        "--compare",
        action="store_true"
    )

    args = parser.parse_args()

    if args.prepare:
        prepare_reviews(args.prepare)

    elif args.score:
        score_version(args.score)

    elif args.compare:
        compare_versions()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()