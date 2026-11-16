from app.agents.workflow import attach_entitlement_review


CLAUSES = [
    "DGCA:3.3.1",
    "DGCA:3.3.2",
    "DGCA:3.3.3",
    "DGCA:3.3.4",
    "DGCA:3.8.1"
]


def passages():
    return [
        {
            "clause_id": clause,
            "document": "DGCA",
            "page": 5,
            "passage": "Verified test passage"
        }
        for clause in CLAUSES
    ]


def test_decline_route_is_preserved():
    evidence = passages()

    analysis = {
        "disruption_type": "cancellation",
        "notice_minutes": 90,
        "block_time_minutes": 150,
        "alternate_flight_offered": True,
        "alternate_flight_accepted": True,
        "contact_details_provided": True,
        "contradictions": []
    }

    entitlement = {
        "retrieved_passages": evidence,
        "citation_verification": {
            "status": "passed",
            "verified_count": len(evidence),
            "rejected_count": 0
        }
    }

    result = attach_entitlement_review(
        {},
        analysis,
        entitlement
    )

    assert result["route"] == "decline"
    assert result["verification_passed"] is True
    assert result["human_escalation"] is False

    assert (
        result["monetary_compensation"]["amount_inr"]
        == 0
    )


def test_failed_citations_block_routing():
    evidence = passages()

    analysis = {
        "disruption_type": "cancellation",
        "notice_minutes": 90,
        "block_time_minutes": 150,
        "alternate_flight_offered": True,
        "alternate_flight_accepted": True,
        "contact_details_provided": True,
        "contradictions": []
    }

    entitlement = {
        "retrieved_passages": evidence,
        "citation_verification": {
            "status": "failed",
            "verified_count": 0,
            "rejected_count": 5
        }
    }

    result = attach_entitlement_review(
        {},
        analysis,
        entitlement
    )

    assert result["route"] == "request-further-evidence"
    assert result["verification_passed"] is False
    assert result["human_escalation"] is True