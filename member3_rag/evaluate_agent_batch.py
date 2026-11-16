import argparse
import hashlib
import inspect
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
BACKEND_DIR = PROJECT_DIR / "backend"
CASES_FILE = BASE_DIR / "claim_evaluation_cases.json"
RESULTS_DIR = BASE_DIR / "agent_evaluation_results"

PROMPT_VERSIONS = [
    "v1-basic",
    "v2-exception-aware"
]

ROUTES = {
    "SC01": ("BLR", "DEL"),
    "SC02": ("BLR", "DEL"),
    "SC03": ("BLR", "DEL"),
    "SC04": ("BLR", "DEL"),
    "SC05": ("BLR", "DEL"),
    "SC06": ("BLR", "DEL"),
    "SC07": ("BLR", "DEL"),
    "SC08": ("BLR", "DEL"),
    "SC09": ("BLR", "DEL"),
    "SC10": ("BLR", "DEL"),
    "SC11": ("BLR", "DEL"),
    "SC12": ("BLR", "DEL"),
    "SC13": ("BLR", "DEL"),
    "SC14": ("BLR", "DXB"),
    "SC15": ("BLR", "DEL"),
    "SC16": ("BLR", "DEL"),
    "SC17": ("BLR", "DEL"),
    "SC18": ("BLR", "DEL"),
    "SC20": ("BLR", "DEL"),
    "SC21": ("CDG", "FRA")
}


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary = path.with_suffix(".tmp")

    temporary.write_text(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
            default=str
        ),
        encoding="utf-8"
    )

    temporary.replace(path)


def load_json(path):
    if not path.exists():
        return {}

    return json.loads(
        path.read_text(encoding="utf-8")
    )


def check_interface():
    backend_path = str(BACKEND_DIR)

    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    from app.agent_runner import run_agents

    parameters = inspect.signature(run_agents).parameters

    if "prompt_version" not in parameters:
        raise RuntimeError(
            "The installed agent runner does not support "
            "prompt_version."
        )

    return run_agents


def prepare_claim(case):
    category = case["category"]

    valid_types = {
        "delay",
        "cancellation",
        "denied_boarding",
        "downgrading"
    }

    disruption = (
        category if category in valid_types else None
    )

    claim = {
        "description": case["claim"],
        "reported_disruption": disruption
    }

    route = ROUTES.get(case["id"])

    if route:
        claim["origin"] = route[0]
        claim["destination"] = route[1]

    if case["id"] == "SC21":
        claim["reported_disruption"] = "cancellation"

    return claim


def claim_fingerprint(claim, version):
    data = json.dumps(
        {
            "claim": claim,
            "prompt_version": version
        },
        sort_keys=True
    )

    return hashlib.sha256(
        data.encode("utf-8")
    ).hexdigest()


def normalize_citations(citations):
    passages = []

    if not isinstance(citations, list):
        return passages

    for citation in citations:
        if not isinstance(citation, dict):
            continue

        text = (
            citation.get("text")
            or citation.get("passage")
        )

        if not text:
            continue

        passages.append({
            "clause_id": citation.get("clause_id"),
            "document": citation.get("document"),
            "page": citation.get("page"),
            "passage": text
        })

    return passages


def classify_result(response, citations):
    scope = response.get("regulatory_scope") or {}
    verification = response.get("citation_verification") or {}
    analysis = response.get("analysis") or {}

    scope_status = scope.get("status")
    verification_status = verification.get("status")

    if scope_status in {"outside", "unknown"}:
        return "completed"

    if scope_status != "supported":
        return "needs_review"

    missing = analysis.get("missing_fields") or []

    if "claim_analysis_unavailable" in missing:
        return "needs_review"

    if verification_status != "passed":
        return "needs_review"

    if verification.get("rejected_count", 0) != 0:
        return "needs_review"

    if not citations:
        return "needs_review"

    return "completed"


def run_scenario(case, version, run_agents):
    claim = prepare_claim(case)

    response = run_agents(
        claim,
        prompt_version=version
    )

    if not isinstance(response, dict):
        raise ValueError("Invalid agent response")

    recorded_version = response.get("prompt_version")

    if recorded_version != version:
        raise RuntimeError(
            f"Prompt version mismatch: "
            f"requested {version}, received {recorded_version}"
        )

    review = response.get("entitlement_review") or {}
    verification = response.get("citation_verification") or {}

    citations = normalize_citations(
        response.get("citations") or []
    )

    status = classify_result(response, citations)

    return {
        "scenario_id": case["id"],
        "category": case["category"],
        "claim": case["claim"],
        "input_claim": claim,
        "input_fingerprint": claim_fingerprint(claim, version),
        "expected_outcome": case["expected_outcome"],
        "expected_route": case["expected_route"],
        "expected_clauses": case["expected_clauses"],
        "prompt_version": recorded_version,
        "status": status,
        "agent_route": response.get("route"),
        "agent_outcome": response.get("outcome"),
        "agent_recommendation": review.get("recommendation"),
        "agent_reasoning": (
            review.get("reasoning")
            or response.get("basis")
        ),
        "analysis": response.get("analysis") or {},
        "entitlement_review": review,
        "supporting_clause_ids": review.get(
            "supporting_clause_ids", []
        ),
        "citations": citations,
        "retrieved_passages": citations,
        "context_source": "final_verified_citations",
        "full_retrieval_context_available": False,
        "verified": response.get("verified"),
        "citation_verification": verification,
        "monetary_compensation": response.get(
            "monetary_compensation"
        ),
        "airport_assistance": response.get(
            "airport_assistance"
        ),
        "regulatory_scope": response.get(
            "regulatory_scope"
        ),
        "tool_calls": response.get("tool_calls", []),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def evaluate(versions, delay, limit):
    cases = json.loads(
        CASES_FILE.read_text(encoding="utf-8")
    )

    if limit is not None:
        if limit < 1:
            raise ValueError("Limit must be positive")

        cases = cases[:limit]

    try:
        run_agents = check_interface()

    except Exception as error:
        print(f"SETUP ERROR: {error}")
        return

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    for version in versions:
        results_file = RESULTS_DIR / f"{version}.json"

        results = load_json(results_file)

        print(f"\nPROMPT VERSION: {version}")
        print("=" * 45)

        for case in cases:
            case_id = case["id"]
            claim = prepare_claim(case)

            fingerprint = claim_fingerprint(
                claim,
                version
            )

            existing = results.get(case_id)

            if (
                isinstance(existing, dict)
                and existing.get("status") == "completed"
                and existing.get("input_fingerprint") == fingerprint
            ):
                print(f"{case_id} | SKIPPED")
                continue

            print(f"\nRunning {case_id}...", flush=True)

            try:
                result = run_scenario(
                    case,
                    version,
                    run_agents
                )

                results[case_id] = result

                print(
                    f"{case_id} | "
                    f"{result['status'].upper()} | "
                    f"Route: {result['agent_route']} | "
                    f"Citations: {len(result['citations'])}"
                )

                if result["status"] == "needs_review":
                    print(
                        "Response needs investigation before scoring."
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

                error_text = str(error)

                if (
                    "429" in error_text
                    or "503" in error_text
                    or "RESOURCE_EXHAUSTED" in error_text
                ):
                    print("API error. Progress saved.")
                    return

                if "Prompt version mismatch" in error_text:
                    return

            save_json(results_file, results)

            if delay > 0:
                time.sleep(delay)

        completed = sum(
            isinstance(item, dict)
            and item.get("status") == "completed"
            for item in results.values()
        )

        print("\n" + "=" * 45)
        print(f"Version: {version}")
        print(f"Completed: {completed}/{len(cases)}")
        print(f"Results saved to: {results_file}")


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