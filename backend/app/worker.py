import logging

import redis

from app.agent_runner import run_agents
from app.runs import finish_run, start_run
from app.task_queue import wait_for_run

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worker")


def process_run(run_id):
    claim = start_run(run_id)
    if claim is None:
        logger.warning("Run %s not found", run_id)
        return

    try:
        result = run_agents(claim)
    except Exception as error:
        logger.exception("Run %s failed", run_id)
        finish_run(run_id, error=str(error))
        return

    finish_run(run_id, result=result)
    logger.info("Run %s completed", run_id)


def main():
    logger.info("Worker started")
    while True:
        try:
            run_id = wait_for_run()
        except redis.RedisError:
            logger.exception("Could not read from Redis")
            continue
        if run_id:
            process_run(run_id)


if __name__ == "__main__":
    main()
