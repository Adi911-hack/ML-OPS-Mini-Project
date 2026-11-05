from uuid import uuid4

from fastapi import FastAPI, status

from app.schemas import ClaimAccepted, ClaimRequest

app = FastAPI(title="Air Passenger Claim Triage API")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/claims", response_model=ClaimAccepted, status_code=status.HTTP_202_ACCEPTED)
def submit_claim(claim: ClaimRequest):
    return ClaimAccepted(run_id=str(uuid4()), status="queued")
