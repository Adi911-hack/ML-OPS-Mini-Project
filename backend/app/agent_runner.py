
from app.agents.workflow import run_claim_agents


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


def run_agents(claim):
    agent_claim = prepare_agent_claim(claim)

    workflow_result = run_claim_agents(agent_claim)

    analysis = workflow_result["analysis"]
    entitlement = workflow_result["entitlement"]

    review = entitlement.get("entitlement_review") or {}

    reason = (
        review.get("reasoning")
        or entitlement.get("reasoning")
        or "Human review is required."
    )

    return {
        "outcome": "escalated",
        "route": "request-further-evidence",
        "basis": reason,
        "citations": [],
        "verified": False,
        "escalation_reason": (
            entitlement.get("escalation_reason")
            or reason
        ),
        "prompt_version": "v1",
        "analysis": analysis,
        "entitlement_review": review,
        "citation_verification": entitlement.get(
            "citation_verification",
            {}
        ),
        "tool_calls": entitlement.get("tool_calls", [])
    }
