from app.agents.workflow import attach_entitlement_review


CLAUSES = [
    "DGCA:3.3.1",
    "DGCA:3.3.2",
    "DGCA:3.3.3",
    "DGCA:3.3.4",
    "DGCA:3.8.1"
]


def make_passages():
    return [
        {
            "clause_id": clause,
            "document": "DGCA",
            "page": 5,
            "passage": "Verified test passage"
        }
        for clause in CLAUSES
    ]


def make_analysis():
    return {
        "disruption_type": "cancellation",
        "notice_minutes": 90,
        "block_time_minutes": 150,
        "alternate_flight_offered": False,
        "alternate_flight_accepted": False,
        "contact_details_provided": True,
        "booked_one_way_basic_fare": 6000,
        "airline_fuel_charge": 500,
        "contradictions": [],
        "cancellation_cause": "ordinary"
    }


def make_entitlement(verification_passed=True):
    passages = make_passages()

    return {
        "retrieved_passages": passages,
        "citation_verification": {
            "status": (
                "passed" if verification_passed else "failed"
            ),
            "verified_count": (
                len(passages) if verification_passed else 0
            ),
            "rejected_count": (
                0 if verification_passed else len(passages)
            )
        }
    }


def make_eligibility_review():
    return {
        "fare_status": "verified",
        "exception_status": "ruled_out",
        "alternate_refund_status": "confirmed"
    }


def test_verified_evidence_allows_payment():
    result = attach_entitlement_review(
        {},
        make_analysis(),
        make_entitlement()
    )

    assert result["route"] == "pay-as-computed"
    assert result["verification_passed"] is True
    assert result["human_escalation"] is False

    assert (
        result["monetary_compensation"]["amount_inr"]
        == 6500
    )


def test_unknown_cancellation_cause_blocks_payment():
    analysis = make_analysis()
    analysis["cancellation_cause"] = None

    result = attach_entitlement_review(
        {},
        analysis,
        make_entitlement()
    )

    assert result["route"] == "request-further-evidence"
    assert result["verification_passed"] is False
    assert result["human_escalation"] is True
    assert result["monetary_compensation"]["amount_inr"] is None


def test_extraordinary_circumstances_escalate():
    analysis = make_analysis()
    analysis["cancellation_cause"] = "extraordinary"

    result = attach_entitlement_review(
        {},
        analysis,
        make_entitlement()
    )

    assert result["route"] == "request-further-evidence"
    assert result["verification_passed"] is False
    assert result["human_escalation"] is True


def test_disputed_cancellation_cause_escalates():
    analysis = make_analysis()
    analysis["cancellation_cause"] = "disputed"

    result = attach_entitlement_review(
        {},
        analysis,
        make_entitlement()
    )

    assert result["route"] == "request-further-evidence"
    assert result["verification_passed"] is False
    assert result["human_escalation"] is True


def test_contradictions_block_payment():
    analysis = make_analysis()
    analysis["contradictions"] = [
        "Passenger statements contain conflicting information"
    ]

    result = attach_entitlement_review(
        {},
        analysis,
        make_entitlement()
    )

    assert result["route"] == "request-further-evidence"
    assert result["verification_passed"] is False
    assert result["human_escalation"] is True


def test_failed_citations_block_payment():
    result = attach_entitlement_review(
        {},
        make_analysis(),
        make_entitlement(verification_passed=False),
        eligibility_review=make_eligibility_review()
    )

    assert result["route"] == "request-further-evidence"
    assert result["verification_passed"] is False
    assert result["human_escalation"] is True