# Load Testing Results

## Project
Air Passenger Claim Triage System

## Test Environment
- Deployment: Docker Compose
- Load testing tool: Locust 2.47.0
- Model provider: Deterministic stub
- Simulated model delay: 500 ms per model operation
- API: FastAPI
- Queue: Redis
- Database: PostgreSQL
- Regulatory retrieval: RAG
- Test duration: 2 minutes per scenario

## Purpose

Evaluate claim submission responsiveness and end-to-end asynchronous claim processing under increasing concurrent load.

The stub model was used to avoid external Gemini API requests and rate-limit dependencies.

## Predeclared Performance Targets

The following targets were committed before testing:

- Claim submission p95: Below 500 ms
- End-to-end claim processing p95: Below 10 seconds
- HTTP request failure rate: Below 1%
- Completed claim processing runs: At least 99%

## Results

| Concurrent Users | Submission p95 | Processing p95 | Submitted Claims | Processing Failures |
|---|---|---|---|---|
| 10 | 80 ms | 8,800 ms | 60 | 0 |
| 25 | 120 ms | 30,000 ms | 122 | 75 of 120 measured runs |
| 50 | 220 ms | 31,000 ms | 221 | 196 of 220 measured runs |

## Observations

### Claim Submission

All claim submission requests returned successfully during the three tests.

Submission p95 remained below the declared 500 ms target:

- 10 users: 80 ms
- 25 users: 120 ms
- 50 users: 220 ms

The claim submission endpoint therefore met its latency target at all tested concurrency levels.

### End-to-End Processing

At 10 concurrent users, all 60 measured claim processing runs completed successfully.

Processing p95 was approximately 8.8 seconds, meeting the declared 10-second target.

At 25 and 50 concurrent users, processing latency increased significantly.

Many runs exceeded the Locust monitoring timeout of 30 seconds.

These timeouts indicate that the test client did not observe completion within the timeout window. They do not necessarily indicate permanent processing failures.

The end-to-end p95 target was not met at 25 or 50 users.

### Resource Utilization

Docker resource inspection showed no obvious memory exhaustion.

The worker used approximately 498 MiB of memory during inspection.

The API remained responsive while asynchronous processing experienced increasing delays.

A likely explanation is that claims were entering the processing queue faster than the available worker capacity could process them.

This requires further investigation before identifying a confirmed root cause.

## Conclusion

The system successfully accepted claims under all tested concurrency levels.

The asynchronous processing pipeline met its declared latency target at 10 users but exceeded the target under higher concurrency.

The results demonstrate that API submission responsiveness and end-to-end claim processing throughput must be evaluated separately.

Potential future improvements include additional worker capacity, queue monitoring, and profiling regulatory retrieval and agent execution.

## Reproducibility

The test implementation is located in:

load_testing/claims_locustfile.py

The declared targets are documented in:

load_testing/PERFORMANCE_TARGETS.md

Raw Locust CSV results are stored in:

load_testing/results/

The stub model is enabled using:

MODEL_PROVIDER=stub

STUB_MODEL_DELAY_MS=500

Load testing uses the Docker Compose override:

docker-compose.stub-loadtest.yml

## Limitations

Results were collected on a local Docker Desktop environment.

Performance may vary with hardware, available resources, and concurrent background processes.

The stub model simulates inference latency but does not reproduce the full behavior or latency distribution of Gemini.

The reported processing p95 values at higher concurrency are affected by the 30-second client timeout.

These results should not be interpreted as production capacity guarantees.