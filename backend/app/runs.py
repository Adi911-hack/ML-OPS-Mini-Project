from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update

from app.database import SessionLocal
from app.models import Run
from app.schemas import RunResponse, RunStatus


def to_response(run):
    return RunResponse(
        run_id=run.id,
        status=run.status,
        created_at=run.created_at,
        updated_at=run.updated_at,
        result=run.result,
        error=run.error,
    )


def create_run(claim):
    with SessionLocal() as session:
        run = Run(claim=claim.model_dump(mode="json"), status=RunStatus.queued.value)
        session.add(run)
        session.commit()
        return run.id


def get_run(run_id):
    with SessionLocal() as session:
        run = session.get(Run, run_id)
        return to_response(run) if run else None


def count_runs():
    with SessionLocal() as session:
        return session.scalar(select(func.count()).select_from(Run))


def start_run(run_id):
    with SessionLocal() as session:
        run = session.get(Run, run_id)
        if run is None or run.status != RunStatus.queued.value:
            return None
        run.status = RunStatus.running.value
        session.commit()
        return run.claim


def finish_run(run_id, result=None, error=None):
    with SessionLocal() as session:
        run = session.get(Run, run_id)
        if run is None or run.status not in (RunStatus.queued.value, RunStatus.running.value):
            return
        run.status = RunStatus.failed.value if error else RunStatus.completed.value
        run.result = result
        run.error = error
        session.commit()


def fail_stale_runs(max_age_seconds):
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=max_age_seconds)
    with SessionLocal() as session:
        outcome = session.execute(
            update(Run)
            .where(
                Run.status.in_([RunStatus.queued.value, RunStatus.running.value]),
                Run.updated_at < cutoff,
            )
            .values(
                status=RunStatus.failed.value,
                error="Run did not complete within the time limit",
            )
        )
        session.commit()
        return outcome.rowcount
