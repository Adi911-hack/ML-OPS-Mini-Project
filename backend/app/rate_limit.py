import logging
import time

from redis import RedisError

from app.config import settings
from app.task_queue import client

logger = logging.getLogger(__name__)

WINDOW_SECONDS = 60


def is_rate_limited(client_id):
    window = int(time.time() // WINDOW_SECONDS)
    key = f"rate_limit:{client_id}:{window}"

    try:
        pipeline = client.pipeline()
        pipeline.incr(key)
        pipeline.expire(key, WINDOW_SECONDS * 2)
        count = pipeline.execute()[0]
    except RedisError:
        logger.exception("Rate limit check failed")
        return False

    return count > settings.rate_limit_per_minute
