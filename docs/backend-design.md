# Backend Design Notes

Notes for the report. Owner: Member 1 (backend, API, validation, queue, Docker).

## Request flow

1. `POST /claims` checks the per-client rate limit, then validates the claim.
2. An invalid claim is quarantined with field-level errors. No run is created.
3. A valid claim is stored as a run with status `queued`, and its ID is pushed
   onto a Redis queue. The caller receives the run ID at once (202).
4. A worker takes the ID, marks the run `running`, calls `run_agents(claim)`,
   and stores the result as `completed` or the error as `failed`.
5. The caller polls `GET /runs/{run_id}` until the status is final.

## Decisions and alternatives rejected

**Polling instead of callbacks (A4).** Runs take several seconds or more, so
the request returns a run ID immediately. Polling was chosen because the client
is a simple web page that cannot receive callbacks without exposing its own
endpoint, and because everything runs locally. The cost is extra status
requests. Rate limiting therefore applies to `POST /claims` only.

**Redis list as the queue.** The API pushes run IDs and workers take them with a
blocking pop. This is simple and supports any number of workers. Celery was
rejected as more setup than the project needs. The weakness is that a run taken
by a worker that then crashes is lost from the queue (see INC-001). This is
handled by failing runs that do not finish within `RUN_TIMEOUT_SECONDS`, so a
lost run is reported as failed rather than left pending. A queue with
acknowledgements, such as Redis Streams, would allow retries and is a possible
improvement.

**Validation at the boundary (F2, D1).** Pydantic enforces types, ranges,
categories, unknown-field rejection, and cross-field rules before any run
exists. Optional facts such as block time may be missing without rejection,
because the agents can route such claims to request further evidence. A
claim outside the corpus is not rejected either, so that it can be escalated
(F7).

**Quarantine in Postgres.** Rejected requests are stored with their errors so
they can be inspected later. `GET /runs/count` shows that a rejected claim
creates no run (demonstration item 4).

**Postgres for records, Redis for transient state.** Runs, quarantine, and
feedback must survive restarts, so they are in Postgres. Redis holds only the
queue and rate-limit counters.

**Rate limiting before validation (D7).** The limit is checked before the
request body is read, so a client sending malformed requests cannot flood the
quarantine table. It uses a fixed one-minute window per client address. If
Redis is unavailable the check is skipped, and claim submission then fails at
the queue with 503.

## Deployment boundaries (D3)

| Service | Why it is separate |
|---|---|
| api | Light image without ML packages. Starts fast and scales with request rate |
| agent-worker | Heavy image with the models, packages, and clause index. Scales with run volume using `--scale`, and is restarted automatically if it crashes without affecting the API |
| postgres | Persistent records, with its own data volume |
| redis | Queue and counters, shared by the API and all workers |

**Index built into the worker image.** The clause index is built while the
worker image is built, and the build fails if the index is empty. Every worker
therefore starts with a complete, identical index, and no worker can query it
before it is ready. Building it on the host and mounting it was rejected because
it breaks a clean clone and runs work outside the containers. Building it into a
shared volume at startup was rejected because workers could start before
indexing finished. The cost is a larger image and a rebuild to re-index.

## Measured results so far

- Stub agent runs completed in 2.2 seconds after the first run.
- Three workers shared six runs, confirming `--scale` works.
- The rate limit allowed 60 requests per minute and returned 429 for the rest.
- With real agents, the section 4.1 claim completed in about 6 seconds, with
  10 citations verified and 0 rejected.

## Known limitations

- Failed runs are not retried automatically.
- The rate limit identifies clients by address only.
- Routing is not final: every run is currently escalated for human review.
