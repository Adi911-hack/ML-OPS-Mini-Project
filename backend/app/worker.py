import logging
import time

import redis
from sqlalchemy.exc import SQLAlchemyError

from app.agent_runner import run_agents
from app.config import settings
from app.runs import fail_stale_runs, finish_run, start_run
from app.task_queue import wait_for_run

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worker")

STALE_CHECK_SECONDS = 30


def process_run(run_id):
    claim = start_run(run_id)
    if claim is None:
        logger.warning("Run %s skipped: not found or not queued", run_id)
        return

    try:
        result = run_agents(claim)
    except Exception as error:
        logger.exception("Run %s failed", run_id)
        finish_run(run_id, error=str(error))
        return

    finish_run(run_id, result=result)
    logger.info("Run %s completed", run_id)


def check_stale_runs():
    try:
        count = fail_stale_runs(settings.run_timeout_seconds)
    except SQLAlchemyError:
        logger.exception("Could not check for stale runs")
        return
    if count:
        logger.warning("Marked %s stale runs as failed", count)


def main():
    logger.info("Worker started")
    last_check = 0
    while True:
        if time.monotonic() - last_check >= STALE_CHECK_SECONDS:
            check_stale_runs()
            last_check = time.monotonic()

        try:
            run_id = wait_for_run()
        except redis.RedisError:
            logger.exception("Could not read from Redis")
            time.sleep(1)
            continue

        if run_id:
            try:
                process_run(run_id)
            except SQLAlchemyError:
                logger.exception("Database error while processing run %s", run_id)


if __name__ == "__main__":
    main()
