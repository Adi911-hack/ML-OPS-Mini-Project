
from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from opentelemetry import trace

from app.agents.claim_analyst import analyze_claim
from app.agents.entitlement_agent import evaluate_entitlement
from app.agents.entitlement_reasoner import review_entitlement
from app.agents.rag_adapter import search_documents, lookup_clause
from app.agents.entitlement_agent import safe_escalation


tracer = trace.get_tracer(__name__)


class ClaimState(TypedDict, total=False):
    claim: dict
    analysis: dict
    entitlement: dict
    run_id: str | None


def set_run_id(span, run_id):
    if run_id is not None:
        span.set_attribute("run_id", str(run_id))


def normalize_claim_analysis(claim, analysis):
    if hasattr(analysis, "model_dump"):
        analysis = analysis.model_dump(mode="json")

    analysis = dict(analysis)

    fields = [
        "airline",
        "notice_minutes",
        "block_time_minutes",
        "alternate_flight_offered",
        "alternate_flight_accepted",
        "contact_details_provided"
    ]

    for field in fields:
        if field in claim:
            analysis[field] = claim[field]

    if not analysis.get("disruption_type"):
        analysis["disruption_type"] = claim.get("disruption_type")

    missing = set(analysis.get("missing_fields") or [])

    for field in fields:
        if field in claim and claim[field] is not None:
            missing.discard(field)

    if analysis.get("disruption_type") == "cancellation":
        required = [
            "notice_minutes",
            "block_time_minutes",
            "contact_details_provided"
        ]

        for field in required:
            if analysis.get(field) is None:
                missing.add(field)
            else:
                missing.discard(field)

    analysis["missing_fields"] = sorted(missing)

    contradictions = analysis.get("contradictions") or []

    contradictions = [
        item for item in contradictions
        if not (
            "null" in str(item).lower()
            and "disruption_type" in str(item).lower()
        )
    ]

    analysis["contradictions"] = contradictions

    disruption = analysis.get("disruption_type") or "unknown"

    explanation = (
        f"The claim is classified as {disruption}. "
        "Structured claim fields have been preserved. "
    )

    if claim.get("disruption_type") is None:
        explanation += (
            "The disruption type was not supplied as a "
            "structured field; this is missing information, "
            "not a contradiction. "
        )

    if analysis["missing_fields"]:
        explanation += (
            "Missing or unknown fields: "
            + ", ".join(analysis["missing_fields"])
            + ". "
        )

    if contradictions:
        explanation += (
            "Potential contradictions require human review."
        )
    else:
        explanation += "No contradictions were identified."

    analysis["explanation"] = explanation

    return analysis


def attach_entitlement_review(claim, analysis, entitlement):
    result = dict(entitlement)

    verification = result.get("citation_verification") or {}
    passages = result.get("retrieved_passages") or []

    verified = (
        verification.get("status") == "passed"
        and verification.get("rejected_count") == 0
        and verification.get("verified_count") == len(passages)
        and len(passages) > 0
    )

    if not verified:
        result["entitlement_review"] = {
            "route": "request-further-evidence",
            "recommendation": "Human review required",
            "reasoning": (
                "Entitlement reasoning was not performed because "
                "the regulatory evidence did not pass citation checks."
            ),
            "conditions": [],
            "missing_information": [
                "verified_regulatory_evidence"
            ],
            "supporting_clause_ids": [],
            "human_escalation": True,
            "verification_passed": False
        }
    else:
        print(
            "Agent 2: Reviewing entitlement conditions...",
            flush=True
        )

        result["entitlement_review"] = review_entitlement(
            claim,
            analysis,
            passages
        )

    review = result["entitlement_review"]
    result["route"] = "request-further-evidence"
    result["human_escalation"] = True
    result["verification_passed"] = False

    result["monetary_compensation"] = review.get(
        "monetary_compensation",
        {
            "status": "undetermined",
            "amount_inr": None,
            "maximum_cap_inr": None
        }
    )

    result["airport_assistance"] = review.get(
        "airport_assistance",
        {
            "status": "not_assessed",
            "meals_and_refreshments": "not_assessed",
            "hotel_accommodation": "not_assessed"
        }
    )

    return result


def analyst_node(state: ClaimState):
    run_id = state.get("run_id")

    with tracer.start_as_current_span("claim_analyst") as span:
        set_run_id(span, run_id)

        print("Running Agent 1: Claim Analyst...", flush=True)

        raw_analysis = analyze_claim(state["claim"])

        analysis = normalize_claim_analysis(
            state["claim"],
            raw_analysis
        )

        span.set_attribute(
            "claim.disruption_type",
            str(analysis.get("disruption_type", "unknown"))
        )

        span.set_attribute(
            "claim.missing_fields_count",
            len(analysis.get("missing_fields") or [])
        )

        return {"analysis": analysis}


def entitlement_node(state: ClaimState):
    run_id = state.get("run_id")
    analysis = state["analysis"]

    if "claim_analysis_unavailable" in (
        analysis.get("missing_fields") or []
    ):
        reason = (
            "Claim Analyst unavailable after model retries. "
            "Human review is required before entitlement assessment."
        )

        return {
            "entitlement": {
                "route": "request-further-evidence",
                "reasoning": reason,
                "escalation_reason": reason,
                "human_escalation": True,
                "verification_passed": False,
                "retrieved_passages": [],
                "citation_verification": {
                    "status": "not_run",
                    "verified_count": 0,
                    "rejected_count": 0
                },
                "tool_calls": [],
                "entitlement_review": {
                    "route": "request-further-evidence",
                    "reasoning": reason,
                    "supporting_clause_ids": [],
                    "human_escalation": True,
                    "verification_passed": False
                }
            }
        }

    with tracer.start_as_current_span("entitlement_agent") as span:
        set_run_id(span, run_id)

        print("Running Agent 2: Entitlement Agent...", flush=True)

        def traced_search(*args, **kwargs):
            with tracer.start_as_current_span("rag_search") as child:
                set_run_id(child, run_id)
                return search_documents(*args, **kwargs)

        def traced_clause_lookup(*args, **kwargs):
            with tracer.start_as_current_span("rag_clause_lookup") as child:
                set_run_id(child, run_id)
                return lookup_clause(*args, **kwargs)

        try:
            entitlement = evaluate_entitlement(
                state["claim"],
                state["analysis"],
                search_function=traced_search,
                clause_function=traced_clause_lookup
            )
        except Exception as error:
            span.record_exception(error)
            span.set_attribute("entitlement.fallback", True)

            entitlement = safe_escalation(
                "Entitlement assessment encountered an unexpected "
                "model or retrieval failure. Human review is required."
            )

        with tracer.start_as_current_span(
            "citation_verification_result"
        ) as child:
            set_run_id(child, run_id)

            verification = (
                entitlement.get("citation_verification") or {}
            )

            child.set_attribute(
                "citations.status",
                str(verification.get("status", "unknown"))
            )

            child.set_attribute(
                "citations.verified_count",
                int(verification.get("verified_count") or 0)
            )

            child.set_attribute(
                "citations.rejected_count",
                int(verification.get("rejected_count") or 0)
            )

        with tracer.start_as_current_span(
            "entitlement_review"
        ) as child:
            set_run_id(child, run_id)

            entitlement = attach_entitlement_review(
                state["claim"],
                state["analysis"],
                entitlement
            )

            review = entitlement.get("entitlement_review") or {}

            child.set_attribute(
                "review.route",
                str(review.get("route", "unknown"))
            )

            child.set_attribute(
                "review.verified",
                bool(review.get("verification_passed", False))
            )

        return {"entitlement": entitlement}


def create_workflow():
    graph = StateGraph(ClaimState)

    graph.add_node("claim_analyst", analyst_node)
    graph.add_node("entitlement_agent", entitlement_node)

    graph.add_edge(START, "claim_analyst")
    graph.add_edge("claim_analyst", "entitlement_agent")
    graph.add_edge("entitlement_agent", END)

    return graph.compile()


def run_claim_agents(claim, run_id=None):
    workflow = create_workflow()

    result = workflow.invoke(
        {
            "claim": claim,
            "run_id": run_id
        },
        config={"recursion_limit": 24}
    )

    return {
        "status": "completed",
        "analysis": result["analysis"],
        "entitlement": result["entitlement"]
    }
