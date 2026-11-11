# Runbook

Commands are run from the project folder unless stated otherwise.

## 1. Agent runs fail or never complete

**Symptom:** `GET /runs/{run_id}` returns `failed`, or a run stays `queued` or
`running` for more than a few minutes.

**Confirm:**

1. Check the run's error:

        Invoke-RestMethod http://127.0.0.1:8000/runs/RUN_ID | Select-Object status, error

2. Check that a worker is running and read its log:

        docker compose ps
        docker compose logs agent-worker --tail 50

3. Check whether runs are waiting on the queue:

        docker compose exec redis redis-cli llen claim_runs

**Common causes:**

| Error or sign | Cause |
|---|---|
| `API_KEY_INVALID` or `400 INVALID_ARGUMENT` | Wrong or placeholder `GOOGLE_API_KEY` or `MODEL_NAME` in `.env` |
| `429` or `RESOURCE_EXHAUSTED` | Model provider rate limit or quota reached |
| `Run did not complete within the time limit` | No worker processed the run within `RUN_TIMEOUT_SECONDS` |
| Worker not listed, or restarting repeatedly | Worker crashed on start. Its log shows why |
| Queue length keeps growing | Workers are missing or too slow for the load |

**Recover:**

- Bad key or model: correct `.env`, then run `docker compose up -d` to recreate
  the worker. Changing `.env` alone does not reach a running container.
- Rate limit: wait and resubmit, or lower the request rate. For load tests, use
  the stub model instead of the real provider.
- Missing or slow workers: `docker compose up -d --scale agent-worker=3`.
- Runs that failed are not retried automatically. Submit the claim again.

## 2. The system does not start

**Symptom:** `docker compose up` fails, `http://127.0.0.1:8000/health` does not
respond, or Docker Desktop shows the engine stopped.

**Confirm:**

1. Check the engine. Docker Desktop should show "Engine running".
2. Check service health:

        docker compose ps

   `postgres`, `redis`, and `api` should show `healthy`. `agent-worker` starts
   only after `api` is healthy.

3. Read the log of any unhealthy service:

        docker compose logs SERVICE_NAME --tail 50

**Common causes:**

| Error or sign | Cause |
|---|---|
| Docker Desktop shows "WSL needs updating" | Windows Subsystem for Linux is out of date |
| `set ... in .env` | A required setting is missing from `.env` |
| `port is already allocated` | Another program is using port 8000, 5432, or 6379 |
| Build stops at `Index is empty` | The clause index failed to build from the documents |
| Build fails while downloading packages or the model | Network problem during the first build |

**Recover:**

- WSL: run `wsl --update`, then `wsl --shutdown`, and restart Docker Desktop.
  If the update returns 403, retry later or from another network.
- Missing settings: copy `.env.example` to `.env` and fill in every value.
- Port in use: stop the other program, or stop a previous run with
  `docker compose down`.
- Build failure: fix the cause, then run `docker compose up --build -d` again.
- To reset all local data, run `docker compose down -v`. This deletes stored
  runs, quarantine records, and feedback.

See `docs/incident-log.md` for failures that occurred during development.
