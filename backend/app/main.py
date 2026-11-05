import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from redis import RedisError
from sqlalchemy.exc import SQLAlchemyError

from app import models  # noqa: F401
from app.database import Base, engine
from app.quarantine import clean_errors, list_rejected_claims, save_rejected_claim
from app.runs import count_runs, create_run, finish_run, get_run
from app.schemas import ClaimAccepted, ClaimRequest, RunResponse, RunStatus
from app.task_queue import enqueue_run

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="Air Passenger Claim Triage API", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError):
    if request.url.path != "/claims":
        return await request_validation_exception_handler(request, exc)

    errors = clean_errors(exc.errors())
    try:
        quarantine_id = await run_in_threadpool(save_rejected_claim, exc.body, errors)
    except SQLAlchemyError:
        logger.exception("Could not save rejected claim to quarantine")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Claim rejected, but quarantine storage is unavailable", "errors": errors},
        )

    return JSONResponse(
        status_code=422,
        content={"status": "rejected", "quarantine_id": quarantine_id, "errors": errors},
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/claims", response_model=ClaimAccepted, status_code=status.HTTP_202_ACCEPTED)
def submit_claim(claim: ClaimRequest):
    run_id = create_run(claim)
    try:
        enqueue_run(run_id)
    except RedisError:
        logger.exception("Could not queue run %s", run_id)
        finish_run(run_id, error="Could not queue the run")
        raise HTTPException(status_code=503, detail="Queue unavailable, please retry")
    return ClaimAccepted(run_id=run_id, status=RunStatus.queued)


@app.get("/runs/count")
def get_run_count():
    return {"total_runs": count_runs()}


@app.get("/runs/{run_id}", response_model=RunResponse)
def read_run(run_id: str):
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@app.get("/quarantine")
def get_quarantine(limit: int = Query(default=20, ge=1, le=100)):
    return list_rejected_claims(limit)
