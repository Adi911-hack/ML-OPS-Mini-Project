
from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from app.agents.claim_analyst import analyze_claim
from app.agents.entitlement_agent import evaluate_entitlement
from app.agents.entitlement_reasoner import review_entitlement
from app.agents.rag_adapter import search_documents, lookup_clause


class ClaimState(TypedDict, total=False):
    claim: dict
    analysis: dict
    entitlement: dict


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

    result["route"] = "request-further-evidence"
    result["human_escalation"] = True
    result["verification_passed"] = False

    return result


def analyst_node(state: ClaimState):
    print("Running Agent 1: Claim Analyst...", flush=True)

    raw_analysis = analyze_claim(state["claim"])

    analysis = normalize_claim_analysis(
        state["claim"],
        raw_analysis
    )

    return {"analysis": analysis}


def entitlement_node(state: ClaimState):
    print("Running Agent 2: Entitlement Agent...", flush=True)

    entitlement = evaluate_entitlement(
        state["claim"],
        state["analysis"],
        search_function=search_documents,
        clause_function=lookup_clause
    )

    entitlement = attach_entitlement_review(
        state["claim"],
        state["analysis"],
        entitlement
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


def run_claim_agents(claim):
    workflow = create_workflow()

    result = workflow.invoke(
        {"claim": claim},
        config={"recursion_limit": 24}
    )

    return {
        "status": "completed",
        "analysis": result["analysis"],
        "entitlement": result["entitlement"]
    }
