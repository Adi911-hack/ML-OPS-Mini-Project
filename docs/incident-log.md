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
