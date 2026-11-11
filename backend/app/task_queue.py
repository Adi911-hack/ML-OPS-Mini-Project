import json

import redis
from opentelemetry import propagate

from app.config import settings

QUEUE_NAME = "claim_runs"

client = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=10,
)


def enqueue_run(run_id):
    trace_context = {}
    propagate.inject(trace_context)
    message = json.dumps({"run_id": run_id, "trace_context": trace_context})
    client.lpush(QUEUE_NAME, message)


def parse_message(message):
    if not message.startswith("{"):
        return message, {}
    data = json.loads(message)
    return data["run_id"], data.get("trace_context") or {}


def wait_for_run(timeout_seconds=5):
    item = client.brpop(QUEUE_NAME, timeout=timeout_seconds)
    if not item:
        return None, {}
    return parse_message(item[1])
