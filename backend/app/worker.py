import inspect
import logging
import time

import redis
from opentelemetry import propagate, trace
from opentelemetry.trace import SpanKind, Status, StatusCode
from sqlalchemy.exc import SQLAlchemyError

from app.agent_runner import run_agents
from app.config import settings
from app.runs import fail_stale_runs, finish_run, start_run
from app.task_queue import wait_for_run

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("worker")
tracer = trace.get_tracer("app.worker")

STALE_CHECK_SECONDS = 30
AGENTS_ACCEPT_RUN_ID = "run_id" in inspect.signature(run_agents).parameters


def call_agents(claim, run_id):
    if AGENTS_ACCEPT_RUN_ID:
        return run_agents(claim, run_id=run_id)
    return run_agents(claim)


def current_trace_id():
    context = trace.get_current_span().get_span_context()
    return format(context.trace_id, "032x") if context.is_valid else "none"


def process_run(run_id, trace_context=None):
    parent = propagate.extract(trace_context or {})
    with tracer.start_as_current_span(
        "process_run", context=parent, kind=SpanKind.CONSUMER
    ) as span:
        span.set_attribute("run_id", run_id)
        trace_id = current_trace_id()

        claim = start_run(run_id)
        if claim is None:
            logger.warning("run_id=%s trace_id=%s skipped: not found or not queued", run_id, trace_id)
            span.set_attribute("run.outcome", "skipped")
            return

        logger.info("run_id=%s trace_id=%s started", run_id, trace_id)
        started = time.monotonic()

        try:
            result = call_agents(claim, run_id)
        except Exception as error:
            logger.exception("run_id=%s trace_id=%s failed", run_id, trace_id)
            span.record_exception(error)
            span.set_status(Status(StatusCode.ERROR, str(error)))
            span.set_attribute("run.outcome", "failed")
            finish_run(run_id, error=str(error))
            return

        finish_run(run_id, result=result)
        span.set_attribute("run.outcome", "completed")
        logger.info(
            "run_id=%s trace_id=%s completed in %.1fs",
            run_id,
            trace_id,
            time.monotonic() - started,
        )


def warm_up():
    try:
        from member3_rag.rag_interface import get_model
    except ImportError:
        return
    started = time.monotonic()
    try:
        get_model()
    except Exception:
        logger.exception("Embedding model warm-up failed")
        return
    logger.info("Embedding model loaded in %.1fs", time.monotonic() - started)


def check_stale_runs():
    try:
        count = fail_stale_runs(settings.run_timeout_seconds)
    except SQLAlchemyError:
        logger.exception("Could not check for stale runs")
        return
    if count:
        logger.warning("Marked %s stale runs as failed", count)


def main():
    warm_up()
    logger.info("Worker started")
    last_check = 0
    while True:
        if time.monotonic() - last_check >= STALE_CHECK_SECONDS:
            check_stale_runs()
            last_check = time.monotonic()

        try:
            run_id, trace_context = wait_for_run()
        except redis.RedisError:
            logger.exception("Could not read from Redis")
            time.sleep(1)
            continue

        if run_id:
            try:
                process_run(run_id, trace_context)
            except SQLAlchemyError:
                logger.exception("Database error while processing run_id=%s", run_id)


if __name__ == "__main__":
    main()
