
import json

from app.agents.workflow import run_claim_agents


claim = {
    "airline": "IndiGo",
    "flight_number": "6E123",
    "disruption_type": None,
    "scheduled_departure": None,
    "actual_departure": None,
    "notice_minutes": 90,
    "block_time_minutes": None,
    "alternate_flight_offered": True,
    "alternate_flight_accepted": True,
    "contact_details_provided": None,
    "claim_description": (
        "My flight was cancelled. I was informed "
        "90 minutes before departure. The airline "
        "offered another flight four hours later "
        "and I accepted it."
    )
}

try:
    result = run_claim_agents(claim)
    print()
    print("FINAL INTEGRATION RESULT")
    print(json.dumps(result, indent=2))
except Exception as error:
    print("INTEGRATION ERROR:", repr(error))
    raise
