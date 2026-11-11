# Incident Log

## INC-001: Runs stuck in queued (2026-11-05)

**Symptom:** POST /claims returned 202, but runs stayed queued. The Redis queue
length was 0, and the worker logged "Timeout reading from socket".

**Investigation:** Pushing a run ID straight onto Redis with LPUSH completed
normally, so the worker logic itself could run. Two worker instances were also
found running at once, and they were stopped.

**Likely cause:** The worker's blocking Redis wait (5 seconds) was too close to
the client's socket read timeout. A run delivered as the connection timed out
could be removed from the queue without being processed.

**Fix:** Set socket_timeout to 10 seconds, longer than the 5-second wait, and ran
a single worker. Later runs completed with no further timeout errors.

**Follow-up:** A run is still lost if a worker crashes after taking it from the
queue. Runs stuck in queued or running need detection and recovery.

## INC-002: Slow first database connection (2026-11-05)

**Symptom:** Server startup took up to about 2 minutes, and a worker's first run
stayed queued for over a minute.

**Fix:** Changed POSTGRES_HOST and REDIS_HOST from localhost to 127.0.0.1.

**Result:** Runs then completed in 5.4 seconds on the first run and 2.2 seconds on
the next, using a 2-second stub agent.

**Cause status:** Not fully confirmed. Slow localhost name resolution on Windows
is suspected, but it was not measured separately.

## INC-003: Docker engine would not start after WSL update check (2026-11-11)

**Symptom:** Docker Desktop showed "WSL needs updating" and the engine stopped,
so no containers could build or run.

**Investigation:** wsl --update and wsl --update --web-download both failed with
Forbidden (403), error Wsl/UpdatePackage/HTTP_E_STATUS_FORBIDDEN.

**Fix:** A later wsl --update reported the latest version was installed (WSL
3.0.5.0). Ran wsl --shutdown and restarted Docker Desktop, and the engine started.

**Cause status:** The 403 was most likely a network or download-source block. Not
confirmed.

## INC-004: Agent runs failed with an invalid API key (2026-11-11)

**Symptom:** Valid claims were marked failed within seconds of reaching the
worker.

**Confirmation:** The run error showed 400 API_KEY_INVALID from the model
provider, with placeholder text still set as the model name.

**Fix:** Set real GOOGLE_API_KEY and MODEL_NAME values in .env and recreated the
worker with docker compose up -d. All 12 API tests then passed.

**Note:** The backend correctly marked these runs failed rather than returning an
answer.

## INC-005: Worker image build failed on corrupted downloads (2026-11-11)

**Symptom:** docker compose up --build failed twice at the agent and RAG package
step with "THESE PACKAGES DO NOT MATCH THE HASHES", after about 30 minutes.

**Cause:** Package downloads were corrupted on a slow connection (about 150 kB/s).
pip correctly refused them. Each retry downloaded every package again, because
the step disabled pip's download cache.

**Fix:** The agent and RAG package step now uses a Docker build cache for pip
downloads, so a retry only fetches what is missing. The Dockerfile was also
reordered so code changes rebuild only the final layer.

## INC-006: Real agent runs failed with provider overload (2026-11-11)

**Symptom:** Several valid claims were marked failed during testing.

**Confirmation:** The worker log showed 503 UNAVAILABLE from the model provider:
"This model is currently experiencing high demand."

**Behaviour:** The entitlement agent used its fallback research plan, but the run
still failed overall. The backend correctly marked these runs failed rather than
returning an answer.

**Follow-up:** Retries with backoff, a circuit breaker and a fallback path are
needed on every model call (A5).
