import json

from sqlalchemy import select

from app.database import SessionLocal
from app.models import QuarantinedClaim


def clean_errors(raw_errors):
    cleaned = []
    for error in raw_errors:
        if error["type"] == "json_invalid":
            field_path = []
        else:
            field_path = [str(part) for part in error["loc"] if part != "body"]
        cleaned.append(
            {
                "field": ".".join(field_path) or "(whole claim)",
                "type": error["type"],
                "message": error["msg"],
            }
        )
    return cleaned


def save_rejected_claim(body, errors):
    with SessionLocal() as session:
        record = QuarantinedClaim(raw_payload=json.dumps(body, default=str), errors=errors)
        session.add(record)
        session.commit()
        return record.id


def list_rejected_claims(limit):
    with SessionLocal() as session:
        query = select(QuarantinedClaim).order_by(QuarantinedClaim.received_at.desc()).limit(limit)
        return [
            {"quarantine_id": r.id, "received_at": r.received_at.isoformat(), "errors": r.errors}
            for r in session.scalars(query)
        ]
