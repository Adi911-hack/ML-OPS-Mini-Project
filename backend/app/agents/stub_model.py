import os
import time


VALID_DISRUPTIONS = {
    "cancellation",
    "delay",
    "denied_boarding",
    "downgrading"
}


def stub_enabled():
    return os.getenv("MODEL_PROVIDER", "gemini").lower() == "stub"


def simulate_delay():
    delay_ms = int(os.getenv("STUB_MODEL_DELAY_MS", "500"))

    if delay_ms < 0 or delay_ms > 10000:
        raise ValueError("STUB_MODEL_DELAY_MS must be between 0 and 10000")

    time.sleep(delay_ms / 1000)


def stub_analyze_claim(claim):
    simulate_delay()

    data = claim.model_dump(mode="json")

    disruption_type = data.get("disruption_type")

    if disruption_type not in VALID_DISRUPTIONS:
        disruption_type = "unknown"

    fields = [
        "airline",
        "notice_minutes",
        "block_time_minutes",
        "alternate_flight_offered",
        "alternate_flight_accepted",
        "contact_details_provided"
    ]

    missing_fields = [
        field
        for field in fields
        if data.get(field) is None
    ]

    return {
        "disruption_type": disruption_type,
        "airline": data.get("airline"),
        "notice_minutes": data.get("notice_minutes"),
        "block_time_minutes": data.get("block_time_minutes"),
        "alternate_flight_offered": data.get("alternate_flight_offered"),
        "alternate_flight_accepted": data.get("alternate_flight_accepted"),
        "contact_details_provided": data.get("contact_details_provided"),
        "missing_fields": missing_fields,
        "contradictions": [],
        "explanation": (
            "Deterministic stub analysis for load testing. "
            "Structured claim fields were preserved. "
            "No independent AI analysis was performed."
        )
    }


def stub_research_plan(disruption_type):
    simulate_delay()

    from app.agents.entitlement_agent import fallback_plan

    return fallback_plan(disruption_type)