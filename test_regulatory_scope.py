
import pytest

from app import agent_runner
from app.agents.regulatory_scope import check_regulatory_scope


@pytest.mark.parametrize(
    "origin,destination",
    [
        ("BLR", "DEL"),
        ("DEL", "FRA"),
        ("FRA", "DEL"),
        ("MAA", "BOM")
    ]
)
def test_india_routes_supported(origin, destination):
    result = check_regulatory_scope({
        "origin": origin,
        "destination": destination
    })

    assert result["status"] == "supported"


def test_europe_only_route_is_outside_corpus():
    result = check_regulatory_scope({
        "origin": "FRA",
        "destination": "CDG"
    })

    assert result["status"] == "outside"
    assert "outside supplied corpus" in result["reason"]


def test_unknown_airport_escalates():
    result = check_regulatory_scope({
        "origin": "ZZZ",
        "destination": "YYY"
    })

    assert result["status"] == "unknown"


def test_missing_airport_escalates():
    result = check_regulatory_scope({
        "origin": "FRA"
    })

    assert result["status"] == "unknown"


def test_outside_claim_never_calls_agents(monkeypatch):
    def unexpected_workflow(*args, **kwargs):
        raise AssertionError(
            "Out-of-corpus claim reached agent workflow"
        )

    monkeypatch.setattr(
        agent_runner,
        "run_claim_agents",
        unexpected_workflow
    )

    result = agent_runner.run_agents({
        "description": "My Lufthansa flight was cancelled.",
        "reported_disruption": "cancellation",
        "airline": "Lufthansa",
        "origin": "FRA",
        "destination": "CDG"
    }, run_id="scope-test-001")

    assert result["outcome"] == "escalated"
    assert result["route"] == "request-further-evidence"
    assert result["verified"] is False
    assert result["citations"] == []
    assert result["regulatory_scope"]["status"] == "outside"
    assert "outside supplied corpus" in result["basis"]


def test_unknown_route_never_calls_agents(monkeypatch):
    def unexpected_workflow(*args, **kwargs):
        raise AssertionError(
            "Unknown jurisdiction reached agent workflow"
        )

    monkeypatch.setattr(
        agent_runner,
        "run_claim_agents",
        unexpected_workflow
    )

    result = agent_runner.run_agents({
        "description": "My flight was cancelled.",
        "origin": "ZZZ",
        "destination": "YYY"
    })

    assert result["outcome"] == "escalated"
    assert result["verified"] is False
    assert result["regulatory_scope"]["status"] == "unknown"
