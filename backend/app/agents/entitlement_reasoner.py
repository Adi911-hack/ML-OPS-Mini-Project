
REQUIRED_CLAUSES = [
    "DGCA:3.3.1",
    "DGCA:3.3.2",
    "DGCA:3.3.3",
    "DGCA:3.3.4",
    "DGCA:3.8.1"
]


def valid_minutes(value, allow_zero=False):
    if isinstance(value, bool):
        return False

    if not isinstance(value, (int, float)):
        return False

    return value >= 0 if allow_zero else value > 0


def compensation_cap(block_time):
    if not valid_minutes(block_time):
        return None

    if block_time <= 60:
        return 5000

    if block_time <= 120:
        return 7500

    return 10000


def review_entitlement(claim, analysis, verified_passages):
    result = {
        "route": "request-further-evidence",
        "recommendation": "Human review required",
        "reasoning": "",
        "conditions": [],
        "missing_information": [],
        "supporting_clause_ids": [],
        "human_escalation": True,
        "verification_passed": False,
        "monetary_compensation": {
            "status": "undetermined",
            "amount_inr": None,
            "maximum_cap_inr": None
        },
        "airport_assistance": {
            "status": "not_assessed",
            "meals_and_refreshments": "not_assessed",
            "hotel_accommodation": "not_assessed"
        }
    }

    if analysis.get("disruption_type") != "cancellation":
        result["reasoning"] = (
            "Automated entitlement assessment currently "
            "supports cancellation claims only."
        )
        return result

    valid_clauses = {}

    for passage in verified_passages:
        if not isinstance(passage, dict):
            continue

        clause_id = passage.get("clause_id")

        if (
            clause_id
            and passage.get("document")
            and passage.get("passage")
        ):
            valid_clauses[clause_id] = passage

    missing_clauses = [
        clause_id
        for clause_id in REQUIRED_CLAUSES
        if clause_id not in valid_clauses
    ]

    if missing_clauses:
        result["reasoning"] = (
            "Required DGCA cancellation provisions "
            "are missing from the verified evidence."
        )
        result["missing_information"] = missing_clauses
        return result

    result["supporting_clause_ids"] = list(REQUIRED_CLAUSES)

    notice = analysis.get("notice_minutes")
    block_time = analysis.get("block_time_minutes")
    contact = analysis.get("contact_details_provided")
    alternate_offered = analysis.get("alternate_flight_offered")
    alternate_accepted = analysis.get("alternate_flight_accepted")

    missing = result["missing_information"]
    conditions = result["conditions"]

    notice_valid = valid_minutes(notice, allow_zero=True)
    block_valid = valid_minutes(block_time)

    if not notice_valid:
        missing.append("notice_minutes")
        notice_status = "unknown"
    elif notice >= 20160:
        notice_status = "at_least_two_weeks"
    elif notice >= 1440:
        notice_status = "between_24_hours_and_two_weeks"
    else:
        notice_status = "less_than_24_hours"

    conditions.append({
        "name": "cancellation_notice",
        "status": notice_status,
        "value_minutes": notice,
        "clause_id": "DGCA:3.3.1"
    })

    if alternate_accepted is True:
        alternate_status = "accepted"
    elif alternate_accepted is False:
        alternate_status = "not_accepted"
    else:
        alternate_status = "unknown"
        missing.append("alternate_flight_accepted")

    conditions.append({
        "name": "alternate_flight",
        "status": alternate_status,
        "offered": alternate_offered,
        "accepted": alternate_accepted,
        "clause_id": "DGCA:3.3.2"
    })

    if not block_valid:
        missing.append("block_time_minutes")
        block_status = "unknown"
    else:
        block_status = "reported"

    cap = compensation_cap(block_time)

    result["monetary_compensation"]["maximum_cap_inr"] = cap

    conditions.append({
        "name": "flight_block_time",
        "status": block_status,
        "value_minutes": block_time,
        "maximum_cap_inr": cap,
        "clause_id": "DGCA:3.3.2"
    })

    if contact is True:
        contact_status = "reported_provided"
    elif contact is False:
        contact_status = "reported_not_provided"
    else:
        contact_status = "unknown"
        missing.append("contact_details_provided")

    conditions.append({
        "name": "contact_information",
        "status": contact_status,
        "clause_id": "DGCA:3.3.3"
    })

    conditions.append({
        "name": "extraordinary_circumstances",
        "status": "not_assessed",
        "clause_id": "DGCA:3.3.4"
    })

    conditions.append({
        "name": "airport_assistance",
        "status": "needs_evidence",
        "clause_id": "DGCA:3.8.1"
    })

    result["airport_assistance"] = {
        "status": "needs_evidence",
        "meals_and_refreshments": "potentially_applicable",
        "hotel_accommodation": "subject_to_necessity"
    }

    missing.extend([
        "cancellation_cause_and_exception_evidence",
        "airport_reporting_and_waiting_details"
    ])

    if analysis.get("contradictions"):
        result["reasoning"] = (
            "Conflicting claim information requires "
            "human review before entitlement assessment."
        )
        missing.append("resolve_claim_contradictions")
        result["missing_information"] = list(dict.fromkeys(missing))
        return result

    monetary = result["monetary_compensation"]

    if contact is False:
        monetary["status"] = "reported_contact_exclusion"
        result["reasoning"] = (
            "The claim reports that adequate booking contact "
            "information was not provided. DGCA 3.3.3 excludes "
            "financial compensation in that situation. "
            "The reported fact and applicable airport assistance "
            "must still be confirmed."
        )

    elif notice_valid and notice >= 20160:
        monetary["status"] = "notice_exclusion_indicated"
        result["reasoning"] = (
            "The reported cancellation notice was at least "
            "two weeks before departure. Compensation for "
            "insufficient cancellation notice is not indicated "
            "by the reported timing. The notice, alternate "
            "travel or refund, and any outstanding obligations "
            "still require verification."
        )

    elif alternate_accepted is True:
        monetary["status"] = "alternate_flight_accepted"
        result["reasoning"] = (
            "The passenger reports accepting an alternate "
            "flight. DGCA 3.3.2 provides an alternate-flight "
            "option and a compensation-plus-refund option "
            "in applicable circumstances. Confirm the offer, "
            "acceptance, notice and airport assistance before "
            "finalizing the recommendation."
        )

    elif notice_valid and notice < 1440 and contact is True:
        monetary["status"] = "potentially_payable"
        result["reasoning"] = (
            "The reported cancellation notice was less than "
            "24 hours. DGCA 3.3.2 compensation may apply, "
            "subject to alternative travel, fare evidence "
            "and extraordinary-circumstance checks."
        )
        missing.extend([
            "booked_one_way_basic_fare",
            "airline_fuel_charge",
            "confirmed_alternate_travel_or_refund_choice"
        ])

    elif notice_valid and notice >= 1440:
        monetary["status"] = "alternate_or_refund_review"
        result["reasoning"] = (
            "The reported notice was between 24 hours "
            "and two weeks before departure. Verify the "
            "alternate-flight or refund obligation under "
            "DGCA 3.3.1."
        )
        missing.append("alternate_travel_or_refund_confirmation")

    else:
        result["reasoning"] = (
            "The available information is insufficient "
            "for a reliable monetary compensation assessment."
        )

    result["recommendation"] = (
        "Request missing evidence and complete human review"
    )

    result["missing_information"] = list(dict.fromkeys(missing))

    return result
