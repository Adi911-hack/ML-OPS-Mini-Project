import redis

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
    client.lpush(QUEUE_NAME, run_id)


def wait_for_run(timeout_seconds=5):
    item = client.brpop(QUEUE_NAME, timeout=timeout_seconds)
    return item[1] if item else None
