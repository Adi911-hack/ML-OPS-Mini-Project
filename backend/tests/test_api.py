import os
import time

import httpx
import pytest

BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")

VALID_CLAIM = {
    "passenger_name": "Test Passenger",
    "booking_reference": "ABC123",
    "airline": "Test Airline",
    "flight_number": "AI101",
    "origin": "BLR",
    "destination": "DEL",
    "scheduled_departure": "2026-10-20T10:00:00+05:30",
    "description": "My flight was cancelled and I took a later flight.",
}


@pytest.fixture
def client():
    with httpx.Client(base_url=BASE_URL, timeout=10) as http_client:
        yield http_client


def run_count(client):
    return client.get("/runs/count").json()["total_runs"]


def wait_for_finish(client, run_id, seconds=30):
    deadline = time.time() + seconds
    while time.time() < deadline:
        run = client.get(f"/runs/{run_id}").json()
        if run["status"] in ("completed", "failed"):
            return run
        time.sleep(0.5)
    pytest.fail(f"Run {run_id} did not finish in {seconds} seconds")


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_valid_claim_runs_to_completion(client):
    response = client.post("/claims", json=VALID_CLAIM)
    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    run = wait_for_finish(client, response.json()["run_id"])
    assert run["status"] == "completed"
    assert run["result"] is not None


@pytest.mark.parametrize(
    "changes, expected_field",
    [
        ({"booking_reference": "12"}, "booking_reference"),
        ({"block_time_minutes": 0}, "block_time_minutes"),
        ({"reported_disruption": "lost_bag"}, "reported_disruption"),
        ({"unknown_field": "x"}, "unknown_field"),
        ({"destination": "BLR"}, "(whole claim)"),
    ],
)
def test_invalid_claim_is_quarantined_and_starts_no_run(client, changes, expected_field):
    runs_before = run_count(client)
    response = client.post("/claims", json={**VALID_CLAIM, **changes})
    assert response.status_code == 422
    body = response.json()
    assert body["status"] == "rejected"
    assert expected_field in [error["field"] for error in body["errors"]]
    assert run_count(client) == runs_before
    quarantined = client.get("/quarantine", params={"limit": 100}).json()
    assert body["quarantine_id"] in [item["quarantine_id"] for item in quarantined]


def test_malformed_json_is_quarantined(client):
    runs_before = run_count(client)
    response = client.post(
        "/claims", content="{not json", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422
    assert response.json()["status"] == "rejected"
    assert run_count(client) == runs_before


def test_unknown_run_returns_404(client):
    assert client.get("/runs/does-not-exist").status_code == 404


def test_feedback_is_saved_and_counted(client):
    run_id = client.post("/claims", json=VALID_CLAIM).json()["run_id"]
    before = client.get("/feedback/summary").json()
    response = client.post(
        "/feedback",
        json={"run_id": run_id, "satisfactory": False, "reason": "Wrong clause cited"},
    )
    assert response.status_code == 201
    after = client.get("/feedback/summary").json()
    assert after["total"] == before["total"] + 1
    assert after["unsatisfactory"] == before["unsatisfactory"] + 1


def test_feedback_for_unknown_run_returns_404(client):
    response = client.post(
        "/feedback",
        json={"run_id": "does-not-exist", "satisfactory": True, "reason": "Looks correct"},
    )
    assert response.status_code == 404


def test_invalid_feedback_is_rejected_without_quarantine(client):
    response = client.post("/feedback", json={"run_id": "x", "satisfactory": True, "reason": ""})
    assert response.status_code == 422
    assert "errors" not in response.json()
