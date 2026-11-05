from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class QuarantinedClaim(Base):
    __tablename__ = "quarantined_claims"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    raw_payload: Mapped[str] = mapped_column(Text)
    errors: Mapped[list] = mapped_column(JSON)
