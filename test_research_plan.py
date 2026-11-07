
from app.agents.entitlement_agent import (
    ToolRequest,
    ResearchPlan,
    execute_research_plan
)


def fake_search(query):
    return {
        "status": "ok",
        "passages": [
            {
                "clause_id": "TEST:1",
                "document": "test.pdf",
                "page": 1,
                "passage": "Synthetic evidence for testing."
            }
        ]
    }


def fake_lookup(clause_id):
    return {
        "status": "ok",
        "clause": {
            "clause_id": clause_id,
            "document": "test.pdf",
            "page": 1,
            "passage": "Synthetic evidence for testing."
        }
    }


plan = ResearchPlan(
    reasoning="Test retrieval.",
    tool_requests=[
        ToolRequest(
            name="get_claim_fields",
            field_names=["airline"]
        ),
        ToolRequest(
            name="search_corpus",
            query="cancellation compensation"
        ),
        ToolRequest(
            name="get_clause_by_id",
            clause_id="TEST:1"
        )
    ]
)

calls, evidence = execute_research_plan(
    plan,
    {"airline": "IndiGo"},
    fake_search,
    fake_lookup
)

assert len(calls) == 3
assert len(evidence) == 1
assert evidence[0]["clause_id"] == "TEST:1"

print("Research planning and tool execution test PASSED")
