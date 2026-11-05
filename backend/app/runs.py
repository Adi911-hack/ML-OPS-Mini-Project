from sqlalchemy import func, select

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
