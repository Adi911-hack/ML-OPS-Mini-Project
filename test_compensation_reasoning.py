
import pytest

from app.agents.entitlement_reasoner import (
    compensation_cap,
    review_entitlement
)


REQUIRED = [
    "DGCA:3.3.1",
    "DGCA:3.3.2",
    "DGCA:3.3.3",
    "DGCA:3.3.4",
    "DGCA:3.8.1"
]


def evidence():
    return [
        {
            "clause_id": clause_id,
            "document": "DGCA",
            "page": 5,
            "passage": "Verified regulatory test passage"
        }
        for clause_id in REQUIRED
    ]


def analysis(**changes):
    data = {
        "disruption_type": "cancellation",
        "notice_minutes": 90,
        "block_time_minutes": 150,
        "alternate_flight_offered": True,
        "alternate_flight_accepted": None,
        "contact_details_provided": True,
        "contradictions": []
    }
    data.update(changes)
    return data


@pytest.mark.parametrize(
    "minutes,expected",
    [
        (60, 5000),
        (61, 7500),
        (120, 7500),
        (121, 10000),
        (150, 10000)
    ]
)
def test_compensation_caps(minutes, expected):
    assert compensation_cap(minutes) == expected


def test_missing_block_time_has_no_cap():
    assert compensation_cap(None) is None
    assert compensation_cap(0) is None
    assert compensation_cap(True) is None


def test_potential_compensation_needs_evidence():
    result = review_entitlement(
        {},
        analysis(alternate_flight_accepted=False),
        evidence()
    )

    monetary = result["monetary_compensation"]

    assert monetary["status"] == "potentially_payable"
    assert monetary["maximum_cap_inr"] == 10000
    assert monetary["amount_inr"] is None
    assert "booked_one_way_basic_fare" in result["missing_information"]
    assert result["verification_passed"] is False
    assert result["route"] == "request-further-evidence"


def test_accepted_alternative_keeps_assistance_review():
    result = review_entitlement(
        {},
        analysis(alternate_flight_accepted=True),
        evidence()
    )

    assert (
        result["monetary_compensation"]["status"]
        == "alternate_flight_accepted"
    )
    assert (
        result["airport_assistance"]["meals_and_refreshments"]
        == "potentially_applicable"
    )
    assert result["route"] == "request-further-evidence"


def test_contact_exclusion_is_not_automatic_payment():
    result = review_entitlement(
        {},
        analysis(contact_details_provided=False),
        evidence()
    )

    assert (
        result["monetary_compensation"]["status"]
        == "reported_contact_exclusion"
    )
    assert result["monetary_compensation"]["amount_inr"] is None
    assert result["verification_passed"] is False


def test_missing_clauses_blocks_assessment():
    result = review_entitlement(
        {},
        analysis(),
        evidence()[:1]
    )

    assert result["supporting_clause_ids"] == []
    assert result["monetary_compensation"]["status"] == "undetermined"
    assert result["verification_passed"] is False


def test_contradictions_require_review():
    result = review_entitlement(
        {},
        analysis(contradictions=["Conflicting disruption details"]),
        evidence()
    )

    assert "resolve_claim_contradictions" in result["missing_information"]
    assert result["verification_passed"] is False

