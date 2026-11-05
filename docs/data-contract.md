# Data Contract

The API schema is also published at `/openapi.json` and `/docs` when the system is
running. Unknown fields are rejected on `POST /claims` and `POST /feedback`.

## POST /claims

### Required fields

| Field | Type | Rule |
|---|---|---|
| passenger_name | string | 1 to 100 characters |
| booking_reference | string | Exactly 6 characters, A-Z or 0-9 |
| airline | string | 2 to 100 characters |
| flight_number | string | 2 letters or digits, then 1 to 4 digits |
| origin | string | 3 capital letters |
| destination | string | 3 capital letters |
| scheduled_departure | datetime | ISO 8601 with a timezone |
| description | string | 10 to 2000 characters |

### Optional fields

A missing optional field is not a validation error. The agents decide whether
further evidence is needed.

| Field | Type | Rule |
|---|---|---|
| reported_disruption | string | denied_boarding, cancellation, delay, or downgrading |
| notice_minutes | integer | 0 to 525600 |
| block_time_minutes | integer | 1 to 1440 |
| alternate_flight_offered | boolean | |
| alternate_flight_accepted | boolean | |
| alternate_departure | datetime | ISO 8601 with a timezone |
| contact_details_provided | boolean | |

### Cross-field rules

- origin and destination must be different.
- alternate_flight_accepted cannot be true if alternate_flight_offered is false.
- alternate_departure cannot be set if alternate_flight_offered is false.
- alternate_departure must be after scheduled_departure.

### Responses

| Code | Meaning | Body |
|---|---|---|
| 202 | Claim accepted and queued | run_id, status |
| 422 | Claim rejected and quarantined. No run is created | status, quarantine_id, errors |
| 429 | Rate limit exceeded. The request is not processed | detail |
| 503 | Queue or quarantine storage unavailable | detail |

Each error has field, type, and message. A field of `(whole claim)` means the error
applies to the claim as a whole, such as a cross-field rule or malformed JSON.

## GET /runs/{run_id}

Returns run_id, status, created_at, updated_at, result, and error. An unknown ID
returns 404.

### Run status

| Status | Meaning |
|---|---|
| queued | Waiting for a worker |
| running | A worker has started the run |
| completed | Finished. See result |
| failed | Did not complete. See error. Must not be shown as an answer |

Callers poll this endpoint until the status is completed or failed.

## GET /runs/count

Returns total_runs.

## GET /quarantine

Optional query parameter limit, from 1 to 100, default 20. Returns the most recent
rejected claims with quarantine_id, received_at, and errors.

## POST /feedback

| Field | Type | Rule |
|---|---|---|
| run_id | string | An existing run. Otherwise returns 404 |
| satisfactory | boolean | |
| reason | string | 3 to 1000 characters |

Returns 201 with feedback_id.

## GET /feedback/summary

Returns total, satisfactory, unsatisfactory, and satisfaction_rate. The rate is null
when there is no feedback.

## GET /health

Returns status.

## Agent function

The worker calls `run_agents(claim)` in `backend/app/agent_runner.py`. It receives
the validated claim as a dictionary and must return a JSON-serialisable dictionary.
Raising an exception marks the run as failed.

## Proposed: agent result

**Status: proposal, to be agreed by the agent and retrieval owners. Not yet enforced
by the code.**

    {
      "outcome": "routed or escalated",
      "route": "pay-as-computed, request-further-evidence, decline, or null",
      "basis": "Explanation of the entitlement position",
      "citations": [
        {
          "document": "Source document name",
          "clause_id": "Clause identifier",
          "page": 1,
          "text": "Exact retrieved passage"
        }
      ],
      "verified": true,
      "escalation_reason": null,
      "prompt_version": "Prompt version identifier"
    }

The system never authorises a payment. The route is a recommendation for a customer
relations officer.

## Proposed: retrieval tools

**Status: proposal, to be agreed by the agent and retrieval owners.**

    search_corpus(query: str, top_k: int) -> list[citation]
    get_clause_by_id(clause_id: str) -> citation or None
    get_claim_fields(run_id: str) -> dict
