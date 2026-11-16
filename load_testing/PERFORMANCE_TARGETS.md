# Load Testing Performance Targets

## Project
Air Passenger Claim Triage System

## Purpose
Evaluate the performance of the claim submission API and asynchronous claim processing pipeline under concurrent load.

Load tests will use a configurable stub model with simulated response delays to avoid external Gemini API calls and rate limits.

## Declared Performance Targets

| Metric | Target |
|---|---|
| Claim submission API p95 latency | < 500 ms |
| End-to-end claim processing p95 latency | < 10 seconds |
| HTTP request failure rate | < 1% |
| Completed claim processing runs | >= 99% |

## Justification

The claim submission API should respond quickly because claim processing is asynchronous. A p95 latency below 500 milliseconds provides a reasonable responsiveness goal for local Docker deployment.

The end-to-end processing target is 10 seconds at the 95th percentile. This allows additional time for Redis queueing, worker execution, regulatory retrieval, and simulated model inference.

The targets are engineering goals selected before performance measurements. They are not claims about measured system performance.

## Testing Method

Tool: Locust

Environment: Local Docker Compose deployment

AI configuration: Stub model

Test scenarios:
- 10 concurrent users
- 25 concurrent users
- 50 concurrent users

Measurements:
- Request count
- Failure rate
- Average response time
- p95 response time
- End-to-end processing duration
- Completed and failed runs

## Important Notes

HTTP request latency and end-to-end processing latency will be measured separately.

A successful HTTP 202 Accepted response does not mean claim processing has completed.

The stub model must not make external Gemini API requests during load testing.

Actual results will be documented separately after testing.