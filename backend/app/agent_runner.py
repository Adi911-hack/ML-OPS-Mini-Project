
from app.agents.workflow import run_claim_agents


ALLOWED_ROUTES = {
    "pay-as-computed",
    "request-further-evidence",
    "decline"
}


def prepare_agent_claim(claim):
    if hasattr(claim, "model_dump"):
        claim = claim.model_dump(mode="json")

    if not isinstance(claim, dict):
        raise ValueError("Claim must be a dictionary")

    agent_claim = dict(claim)
    description = claim.get("description")

    if not description:
        raise ValueError("Claim description is required")

    agent_claim["claim_description"] = description
    agent_claim["disruption_type"] = claim.get(
        "reported_disruption"
    )

    return agent_claim


def collect_verified_citations(entitlement, review):
    verification = entitlement.get("citation_verification") or {}
    passages = entitlement.get("retrieved_passages") or []

    if not isinstance(passages, list):
        return []

    if (
        verification.get("status") != "passed"
        or verification.get("rejected_count") != 0
        or not passages
        or verification.get("verified_count") != len(passages)
    ):
        return []

    supporting_ids = set(
        review.get("supporting_clause_ids") or []
    )

    if not supporting_ids:
        return []

    citations = []
    seen = set()

    for passage in passages:
        if not isinstance(passage, dict):
            return []

        clause_id = passage.get("clause_id")
        document = passage.get("document")
        page = passage.get("page")
        text = passage.get("passage")

        if (
            not isinstance(clause_id, str)
            or not isinstance(document, str)
            or not isinstance(text, str)
            or not text.strip()
        ):
            return []

        if clause_id not in supporting_ids:
            continue

        identity = (clause_id, document, page, text)

        if identity in seen:
            continue

        seen.add(identity)

        citations.append({
            "document": document,
            "clause_id": clause_id,
            "page": page,
            "text": text
        })

    return citations


def run_agents(claim):
    agent_claim = prepare_agent_claim(claim)
    workflow_result = run_claim_agents(agent_claim)

    analysis = workflow_result["analysis"]
    entitlement = workflow_result["entitlement"]

    review = entitlement.get("entitlement_review") or {}
    verification = entitlement.get("citation_verification") or {}

    citations = collect_verified_citations(
        entitlement,
        review
    )

    decision_verified = (
        review.get("verification_passed") is True
        and entitlement.get("verification_passed") is True
        and bool(citations)
        and verification.get("status") == "passed"
        and verification.get("rejected_count") == 0
    )

    proposed_route = (
        review.get("route")
        or entitlement.get("route")
        or "request-further-evidence"
    )

    if proposed_route not in ALLOWED_ROUTES:
        proposed_route = "request-further-evidence"

    if (
        proposed_route in {"pay-as-computed", "decline"}
        and not decision_verified
    ):
        route = "request-further-evidence"
    else:
        route = proposed_route

    if route == "pay-as-computed":
        outcome = "routed"
    elif route == "decline":
        outcome = "routed"
    else:
        outcome = "escalated"

    reason = (
        review.get("reasoning")
        or entitlement.get("reasoning")
        or "Human review is required."
    )

    escalation_reason = None

    if outcome == "escalated":
        escalation_reason = (
            entitlement.get("escalation_reason")
            or reason
        )

    return {
        "outcome": outcome,
        "route": route,
        "basis": reason,
        "citations": citations,
        "verified": decision_verified,
        "escalation_reason": escalation_reason,
        "prompt_version": "v1",
        "analysis": analysis,
        "entitlement_review": review,
        "citation_verification": verification,
        "tool_calls": entitlement.get("tool_calls", [])
    }
