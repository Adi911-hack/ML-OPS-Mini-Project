
import pytest

from app.agents.entitlement_reasoner import (
    compensation_cap,
    calculate_compensation,
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

    assert result["route"] == "decline"
    assert result["verification_passed"] is True
    assert result["human_escalation"] is False

    assert (
        result["monetary_compensation"]["status"]
        == "not_payable"
    )

    assert result["monetary_compensation"]["amount_inr"] == 0

    assert (
        result["airport_assistance"]["meals_and_refreshments"]
        == "potentially_applicable"
    )

    assert "DGCA:3.3.2" in result["supporting_clause_ids"]

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

@pytest.mark.parametrize(
    "block_time,basic_fare,fuel_charge,expected",
    [
        (45, 3000, 500, 3500),
        (90, 8000, 500, 7500),
        (150, 6000, 500, 6500),
        (150, 12000, 500, 10000),
        (None, 6000, 500, None),
        (150, None, 500, None),
        (150, -100, 500, None),
        (150, True, 500, None)
    ]
)
def test_calculate_compensation(
    block_time,
    basic_fare,
    fuel_charge,
    expected
):
    result = calculate_compensation(
        block_time,
        basic_fare,
        fuel_charge
    )

    assert result == expected

def test_potential_amount_does_not_approve_payment():
    claim_analysis = analysis(
        alternate_flight_offered=False,
        alternate_flight_accepted=False,
        booked_one_way_basic_fare=6000,
        airline_fuel_charge=500
    )

    result = review_entitlement(
        {},
        claim_analysis,
        evidence()
    )

    monetary = result["monetary_compensation"]

    assert monetary["potential_amount_inr"] == 6500
    assert monetary["amount_inr"] is None
    assert result["route"] == "request-further-evidence"
    assert result["verification_passed"] is False

def test_provided_fare_is_not_reported_missing():
    result = review_entitlement(
        {},
        analysis(
            alternate_flight_offered=False,
            alternate_flight_accepted=False,
            booked_one_way_basic_fare=6000,
            airline_fuel_charge=500
        ),
        evidence()
    )

    missing = result["missing_information"]

    assert "booked_one_way_basic_fare" not in missing
    assert "airline_fuel_charge" not in missing

    assert (
        result["monetary_compensation"]["potential_amount_inr"]
        == 6500
    )

    assert result["route"] == "request-further-evidence"

def test_verified_payment_route():
    result = review_entitlement(
        {},
        analysis(
            alternate_flight_offered=False,
            alternate_flight_accepted=False,
            booked_one_way_basic_fare=6000,
            airline_fuel_charge=500
        ),
        evidence(),
        eligibility_review={
            "fare_status": "verified",
            "exception_status": "ruled_out",
            "alternate_refund_status": "confirmed"
        }
    )

    assert result["route"] == "pay-as-computed"
    assert result["verification_passed"] is True
    assert result["human_escalation"] is False

    assert (
        result["monetary_compensation"]["amount_inr"]
        == 6500
    )

    assert (
        result["monetary_compensation"]["status"]
        == "payable"
    )

def test_payment_without_verified_evidence_escalates():
    result = review_entitlement(
        {},
        analysis(
            alternate_flight_offered=False,
            alternate_flight_accepted=False,
            booked_one_way_basic_fare=6000,
            airline_fuel_charge=500
        ),
        evidence()
    )

    assert result["route"] == "request-further-evidence"
    assert result["verification_passed"] is False
    assert result["monetary_compensation"]["amount_inr"] is None

def test_payment_without_verified_evidence_escalates():
    result = review_entitlement(
        {},
        analysis(
            alternate_flight_offered=False,
            alternate_flight_accepted=False,
            booked_one_way_basic_fare=6000,
            airline_fuel_charge=500
        ),
        evidence()
    )

    assert result["route"] == "request-further-evidence"
    assert result["verification_passed"] is False
    assert result["monetary_compensation"]["amount_inr"] is None