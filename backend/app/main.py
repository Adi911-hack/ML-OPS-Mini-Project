import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Query, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app import models  # noqa: F401
from app.database import Base, engine
from app.quarantine import clean_errors, list_rejected_claims, save_rejected_claim
from app.schemas import ClaimAccepted, ClaimRequest

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
    return ClaimAccepted(run_id=str(uuid4()), status="queued")


@app.get("/quarantine")
def get_quarantine(limit: int = Query(default=20, ge=1, le=100)):
    return list_rejected_claims(limit)
