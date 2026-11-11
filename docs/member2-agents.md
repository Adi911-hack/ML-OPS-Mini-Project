# Person 2 — AI Agent Workflow

## Overview

This component implements the AI-assisted passenger claim triage workflow.

Agent 1 analyses a passenger claim and normalizes its structured fields.

Agent 2 selects bounded research tools, retrieves relevant regulatory passages from Person 3's RAG system, verifies retrieved citations against the index, and reviews applicable entitlement conditions.

## Main files

- backend/app/agents/claim_analyst.py — Claim analysis
- backend/app/agents/entitlement_agent.py — Research planning and execution
- backend/app/agents/entitlement_reasoner.py — Entitlement condition review
- backend/app/agents/citation_verifier.py — Citation matching
- backend/app/agents/rag_adapter.py — Person 3 RAG integration
- backend/app/agents/workflow.py — Two-agent orchestration
- backend/app/agents/tools.py — Research tools
- backend/app/agent_runner.py — Backend worker integration

## Current supported behavior

- Structured analysis of cancellation claims
- Regulatory retrieval through the RAG interface
- Citation matching against indexed regulatory passages
- Detection of missing information
- Conservative human escalation for unresolved entitlement conditions
- Integration with the FastAPI worker workflow

Citation matching confirms that retrieved passages correspond to indexed source content. It does not independently establish compensation eligibility.

The current entitlement review supports cancellation conditions. Other disruption types and final compensation approval or rejection require further implementation and verification.

## Dependencies

This component depends on Person 3's member3_rag package.

The RAG package, indexed data, and required source documents must be available before running the complete application.

The Docker development configuration consists of:

- backend/Dockerfile.agents
- backend/requirements-agents.txt
- docker-compose.agents.yml

## Local tests

From the project root with the Python virtual environment active:

PYTHONPATH=backend:. python -m pytest -q

## Docker

Ensure the project .env contains the required backend variables, GOOGLE_API_KEY, and MODEL_NAME.

Run from the project root:

docker compose -f docker-compose.yml -f docker-compose.agents.yml up -d --build

Check the running services:

docker compose -f docker-compose.yml -f docker-compose.agents.yml ps

Check the API health:

curl http://127.0.0.1:8000/health

## Validation performed

- 28 automated Python tests passed locally
- Docker API and worker started successfully
- End-to-end cancellation claim processing completed
- Retrieved RAG passages passed citation matching with zero rejected passages
- The tested cancellation claim was escalated for further evidence rather than automatically approved

## Remaining work

- Extend and validate entitlement logic for delay, denied boarding, and downgrading
- Evaluate additional scenarios and provider failures
- Independently validate regulatory decision outcomes
- Confirm integration on a fresh team checkout after Person 3's RAG branch is merged

## Security

Do not commit API keys, .env files, local virtual environments, user claim responses, or private passenger information.
