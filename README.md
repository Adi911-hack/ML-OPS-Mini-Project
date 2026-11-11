# Air Passenger Compensation Claim Triage Service

Backend for the claim triage service. It validates claims, quarantines rejected
requests, queues valid runs, and processes them with scalable workers.

**Current status:** the worker runs the claim analyst and entitlement agents, with retrieval over the DGCA and airline corpus. Routing is not final: every run is currently escalated for human review. The frontend and monitoring are not yet connected.

## Run the system

You need Docker Desktop with the engine running.

    cp .env.example .env
    docker compose up --build

On Windows PowerShell, use `Copy-Item .env.example .env` for the first command.
Edit the password in `.env` before use, and set `GOOGLE_API_KEY` and `MODEL_NAME`. The first build takes 10 to 20 minutes because it downloads the embedding model and builds the clause index inside the worker image. To run three workers:

    docker compose up --build -d --scale agent-worker=3

API documentation is at http://127.0.0.1:8000/docs

## API

| Method | Path | Purpose |
|---|---|---|
| GET | /health | Service health |
| POST | /claims | Validate and queue a claim. Returns 202 with a run ID, 422 if rejected, or 429 if rate limited |
| GET | /runs/{run_id} | Run status and result. Status is queued, running, completed, or failed |
| GET | /runs/count | Total runs, used to show rejected claims start no run |
| GET | /quarantine | Recent rejected claims with field-level errors |
| POST | /feedback | Mark a result satisfactory or not, with a reason |
| GET | /feedback/summary | Aggregated feedback |

The caller polls `GET /runs/{run_id}` because a run takes too long to hold one
HTTP request open.

## Configuration

All settings are injected at runtime from `.env`. See `.env.example`.
`RATE_LIMIT_PER_MINUTE` limits `POST /claims` per client address.

## Tests

With the system running:

    python -m pip install -r backend/requirements-dev.txt
    python -m pytest backend/tests -q

## Agent integration

The worker calls `run_agents(claim)` in `backend/app/agent_runner.py`. It receives
the validated claim as a dictionary and returns the result as a dictionary. Raising
an exception marks the run as failed.

## Documents

Development failures are recorded in `docs/incident-log.md`.

