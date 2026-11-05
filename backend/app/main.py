from fastapi import FastAPI

app = FastAPI(title="Air Passenger Claim Triage API")


@app.get("/health")
def health():
    return {"status": "ok"}
