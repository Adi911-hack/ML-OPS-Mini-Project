
def review_entitlement(claim, analysis, verified_passages):
    disruption_type = analysis.get("disruption_type")

    result = {
        "route": "request-further-evidence",
        "recommendation": "Human review required",
        "reasoning": "",
        "conditions": [],
        "missing_information": [],
        "supporting_clause_ids": [],
        "human_escalation": True,
        "verification_passed": False
    }

    if disruption_type != "cancellation":
        result["reasoning"] = (
            "This reasoning module currently supports "
            "cancellation claims only."
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

    required_clauses = [
        "DGCA:3.3.1",
        "DGCA:3.3.2",
        "DGCA:3.3.3",
        "DGCA:3.3.4",
        "DGCA:3.8.1"
    ]

    missing_clauses = [
        clause_id
        for clause_id in required_clauses
        if clause_id not in valid_clauses
    ]

    if missing_clauses:
        result["reasoning"] = (
            "Essential cancellation provisions are missing "
            "from the verified regulatory evidence."
        )
        result["missing_information"] = missing_clauses
        return result

    result["supporting_clause_ids"] = required_clauses

    notice = analysis.get("notice_minutes")

    if notice is None:
        result["conditions"].append({
            "name": "cancellation_notice",
            "status": "unknown",
            "clause_id": "DGCA:3.3.1"
        })
        result["missing_information"].append("notice_minutes")
    elif isinstance(notice, (int, float)) and not isinstance(notice, bool) and notice >= 0:
        result["conditions"].append({
            "name": "cancellation_notice",
            "status": "reported",
            "value_minutes": notice,
            "clause_id": "DGCA:3.3.1"
        })
    else:
        result["conditions"].append({
            "name": "cancellation_notice",
            "status": "invalid",
            "clause_id": "DGCA:3.3.1"
        })
        result["missing_information"].append("valid_notice_minutes")

    alternate_offered = analysis.get("alternate_flight_offered")
    alternate_accepted = analysis.get("alternate_flight_accepted")

    if alternate_accepted is True:
        alternate_status = "accepted"
    elif alternate_accepted is False:
        alternate_status = "not_accepted"
    else:
        alternate_status = "unknown"
        result["missing_information"].append(
            "alternate_flight_accepted"
        )

    result["conditions"].append({
        "name": "alternate_flight",
        "status": alternate_status,
        "offered": alternate_offered,
        "accepted": alternate_accepted,
        "clause_id": "DGCA:3.3.2"
    })

    block_time = analysis.get("block_time_minutes")

    if block_time is None:
        result["missing_information"].append(
            "block_time_minutes"
        )
        block_status = "unknown"
    elif isinstance(block_time, bool) or not isinstance(
        block_time, (int, float)
    ) or block_time <= 0:
        result["missing_information"].append(
            "valid_block_time_minutes"
        )
        block_status = "invalid"
    else:
        block_status = "reported"

    result["conditions"].append({
        "name": "flight_block_time",
        "status": block_status,
        "value_minutes": block_time,
        "clause_id": "DGCA:3.3.2"
    })

    contact = analysis.get("contact_details_provided")

    if contact is True:
        contact_status = "reported_provided"
    elif contact is False:
        contact_status = "reported_not_provided"
    else:
        contact_status = "unknown"
        result["missing_information"].append(
            "contact_details_provided"
        )

    result["conditions"].append({
        "name": "contact_information",
        "status": contact_status,
        "clause_id": "DGCA:3.3.3"
    })

    result["conditions"].append({
        "name": "extraordinary_circumstances",
        "status": "not_assessed",
        "clause_id": "DGCA:3.3.4"
    })

    result["missing_information"].append(
        "cancellation_cause_and_exception_evidence"
    )

    result["conditions"].append({
        "name": "airport_assistance",
        "status": "not_assessed",
        "clause_id": "DGCA:3.8.1"
    })

    result["missing_information"].append(
        "airport_reporting_and_waiting_details"
    )

    result["missing_information"] = list(
        dict.fromkeys(result["missing_information"])
    )

    result["reasoning"] = (
        "The cancellation claim has been checked against "
        "the indexed DGCA provisions. The reported notice "
        "period, alternate flight acceptance, contact "
        "information and block time have been recorded. "
        "Outstanding conditions and exceptions still "
        "require assessment. No payment entitlement "
        "has been established."
    )

    return result
