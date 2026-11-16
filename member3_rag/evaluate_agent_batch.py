import argparse
import inspect
import json
import time
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CASES_FILE = BASE_DIR / "claim_evaluation_cases.json"
RESULTS_DIR = BASE_DIR / "agent_evaluation_results"

PROMPT_VERSIONS = [
    "v1-basic",
    "v2-exception-aware"
]


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8"
    )
    temporary.replace(path)


def load_json(path):
    if not path.exists():
        return {}

    return json.loads(path.read_text(encoding="utf-8"))


def prepare_claim(case):
    category = case["category"]

    valid_types = {
        "delay",
        "cancellation",
        "denied_boarding",
        "downgrading"
    }

    disruption_type = (
        category if category in valid_types else None
    )

    return {
        "claim_description": case["claim"],
        "description": case["claim"],
        "disruption_type": disruption_type,
        "reported_disruption": disruption_type
    }


def run_scenario(case, prompt_version):
    from app.agents.claim_analyst import analyze_claim
    from app.agents.entitlement_agent import evaluate_entitlement
    from app.agents.workflow import (
        normalize_claim_analysis,
        attach_entitlement_review
    )
    from app.agents.rag_adapter import (
        search_documents,
        lookup_clause
    )

    signature = inspect.signature(evaluate_entitlement)

    if "prompt_version" not in signature.parameters:
        raise RuntimeError(
            "Shristi's prompt-version update is not installed yet. "
            "Wait for her PR before running this evaluator."
        )

    claim = prepare_claim(case)

    analysis = analyze_claim(claim)

    analysis = normalize_claim_analysis(
        claim,
        analysis
    )

    entitlement = evaluate_entitlement(
        claim,
        analysis,
        search_function=search_documents,
        clause_function=lookup_clause,
        prompt_version=prompt_version
    )

    entitlement = attach_entitlement_review(
        claim,
        analysis,
        entitlement
    )

    recorded_version = entitlement.get("prompt_version")

    if recorded_version != prompt_version:
        raise RuntimeError(
            f"Prompt version mismatch: requested {prompt_version}, "
            f"received {recorded_version}"
        )

    review = entitlement.get("entitlement_review") or {}

    verification = entitlement.get("citation_verification") or {}

    passages = entitlement.get("retrieved_passages") or []

    return {
        "scenario_id": case["id"],
        "category": case["category"],
        "claim": case["claim"],
        "expected_outcome": case["expected_outcome"],
        "expected_route": case["expected_route"],
        "expected_clauses": case["expected_clauses"],
        "prompt_version": recorded_version,
        "analysis": analysis,
        "entitlement_review": review,
        "agent_route": review.get("route"),
        "agent_recommendation": review.get("recommendation"),
        "agent_reasoning": review.get("reasoning"),
        "supporting_clause_ids": review.get(
            "supporting_clause_ids", []
        ),
        "retrieved_passages": passages,
        "citation_verification": verification,
        "tool_calls": entitlement.get("tool_calls", []),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "completed"
    }


def evaluate(versions, delay, limit):
    cases = json.loads(
        CASES_FILE.read_text(encoding="utf-8")
    )

    if limit is not None:
        cases = cases[:limit]

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    for version in versions:
        results_file = RESULTS_DIR / f"{version}.json"

        results = load_json(results_file)

        print(f"\nPROMPT VERSION: {version}")
        print("=" * 45)

        for case in cases:
            case_id = case["id"]

            existing = results.get(case_id)

            if existing and existing.get("status") == "completed":
                print(f"{case_id} | SKIPPED")
                continue

            print(f"\nRunning {case_id}...")

            try:
                result = run_scenario(case, version)

                results[case_id] = result

                print(
                    f"{case_id} | COMPLETED | "
                    f"Route: {result['agent_route']}"
                )

            except Exception as error:
                results[case_id] = {
                    "scenario_id": case_id,
                    "prompt_version": version,
                    "status": "error",
                    "error": str(error),
                    "timestamp": datetime.now(
                        timezone.utc
                    ).isoformat()
                }

                print(f"{case_id} | ERROR: {error}")

                save_json(results_file, results)

                if (
                    "prompt-version update" in str(error)
                    or "Prompt version mismatch" in str(error)
                ):
                    return

                if (
                    "429" in str(error)
                    or "503" in str(error)
                    or "RESOURCE_EXHAUSTED" in str(error)
                ):
                    print(
                        "API limit or service error detected. "
                        "Progress saved. Stop and resume later."
                    )
                    return

            save_json(results_file, results)

            if delay > 0:
                time.sleep(delay)

        completed = sum(
            item.get("status") == "completed"
            for item in results.values()
        )

        print(f"\nCompleted: {completed}/{len(cases)}")
        print(f"Saved to: {results_file}")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--version",
        choices=PROMPT_VERSIONS + ["both"],
        default="both"
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=15
    )

    parser.add_argument(
        "--limit",
        type=int
    )

    args = parser.parse_args()

    versions = (
        PROMPT_VERSIONS
        if args.version == "both"
        else [args.version]
    )

    evaluate(
        versions=versions,
        delay=args.delay,
        limit=args.limit
    )


if __name__ == "__main__":
    main()