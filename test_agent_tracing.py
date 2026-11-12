
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app import agent_runner
from app.agents import workflow


def test_agent_spans_share_worker_trace(monkeypatch):
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    tracer = provider.get_tracer("test")

    monkeypatch.setattr(agent_runner, "tracer", tracer)
    monkeypatch.setattr(workflow, "tracer", tracer)

    def fake_analysis(claim):
        return {
            "disruption_type": "cancellation",
            "airline": "IndiGo",
            "missing_fields": [],
            "contradictions": [],
            "explanation": "Cancellation reported."
        }

    passage = {
        "document": "DGCA",
        "clause_id": "DGCA:3.3.1",
        "page": 5,
        "passage": "Test regulatory passage."
    }

    def fake_entitlement(
        claim,
        analysis,
        search_function,
        clause_function
    ):
        search_function("cancellation")
        clause_function("DGCA:3.3.1")

        return {
            "retrieved_passages": [passage],
            "citation_verification": {
                "status": "passed",
                "verified_count": 1,
                "rejected_count": 0
            },
            "tool_calls": []
        }

    def fake_review(claim, analysis, passages):
        return {
            "route": "request-further-evidence",
            "reasoning": "Human review required.",
            "supporting_clause_ids": ["DGCA:3.3.1"],
            "human_escalation": True,
            "verification_passed": False
        }

    monkeypatch.setattr(
        workflow,
        "analyze_claim",
        fake_analysis
    )

    monkeypatch.setattr(
        workflow,
        "evaluate_entitlement",
        fake_entitlement
    )

    monkeypatch.setattr(
        workflow,
        "review_entitlement",
        fake_review
    )

    monkeypatch.setattr(
        workflow,
        "search_documents",
        lambda *args, **kwargs: []
    )

    monkeypatch.setattr(
        workflow,
        "lookup_clause",
        lambda *args, **kwargs: {"status": "ok"}
    )

    run_id = "test-run-123"

    with tracer.start_as_current_span("process_run") as parent:
        parent.set_attribute("run_id", run_id)

        result = agent_runner.run_agents(
            {
                "description": "My flight was cancelled.",
                "reported_disruption": "cancellation",
                "airline": "IndiGo"
            },
            run_id=run_id
        )

    spans = exporter.get_finished_spans()
    by_name = {span.name: span for span in spans}

    expected = [
        "process_run",
        "agent_runner",
        "prepare_claim",
        "agent_workflow",
        "claim_analyst",
        "entitlement_agent",
        "rag_search",
        "rag_clause_lookup",
        "citation_verification_result",
        "entitlement_review",
        "citation_mapping",
        "decision_routing"
    ]

    for name in expected:
        assert name in by_name
        assert by_name[name].attributes["run_id"] == run_id

    trace_ids = {
        span.context.trace_id
        for span in spans
    }

    assert len(trace_ids) == 1

    assert (
        by_name["agent_runner"].parent.span_id
        == by_name["process_run"].context.span_id
    )

    assert (
        by_name["claim_analyst"].parent.span_id
        == by_name["agent_workflow"].context.span_id
    )

    assert (
        by_name["rag_search"].parent.span_id
        == by_name["entitlement_agent"].context.span_id
    )

    assert (
        by_name["rag_clause_lookup"].parent.span_id
        == by_name["entitlement_agent"].context.span_id
    )

    assert result["route"] == "request-further-evidence"
    assert result["outcome"] == "escalated"
    assert len(result["citations"]) == 1

    provider.shutdown()
