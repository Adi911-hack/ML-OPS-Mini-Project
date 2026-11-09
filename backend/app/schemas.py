from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class DisruptionType(str, Enum):
    denied_boarding = "denied_boarding"
    cancellation = "cancellation"
    delay = "delay"
    downgrading = "downgrading"


class RunStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class ClaimRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    passenger_name: str = Field(min_length=1, max_length=100)
    booking_reference: str = Field(pattern=r"^[A-Z0-9]{6}$")
    airline: str = Field(min_length=2, max_length=100)
    flight_number: str = Field(pattern=r"^[A-Z0-9]{2}[0-9]{1,4}$")
    origin: str = Field(pattern=r"^[A-Z]{3}$")
    destination: str = Field(pattern=r"^[A-Z]{3}$")
    scheduled_departure: AwareDatetime
    description: str = Field(min_length=10, max_length=2000)

    reported_disruption: Optional[DisruptionType] = None
    notice_minutes: Optional[int] = Field(default=None, ge=0, le=525600)
    block_time_minutes: Optional[int] = Field(default=None, gt=0, le=1440)
    alternate_flight_offered: Optional[bool] = None
    alternate_flight_accepted: Optional[bool] = None
    alternate_departure: Optional[AwareDatetime] = None
    contact_details_provided: Optional[bool] = None

    @model_validator(mode="after")
    def check_cross_field_rules(self):
        if self.origin == self.destination:
            raise ValueError("origin and destination must be different")

        if self.alternate_flight_accepted and self.alternate_flight_offered is False:
            raise ValueError("an alternate flight cannot be accepted if none was offered")

        if self.alternate_departure is not None:
            if self.alternate_flight_offered is False:
                raise ValueError("alternate_departure given but no alternate flight was offered")
            if self.alternate_departure <= self.scheduled_departure:
                raise ValueError("alternate_departure must be after scheduled_departure")

        return self


class ClaimAccepted(BaseModel):
    run_id: str
    status: RunStatus


class RunResponse(BaseModel):
    run_id: str
    status: RunStatus
    created_at: datetime
    updated_at: datetime
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    run_id: str = Field(min_length=1, max_length=36)
    satisfactory: bool
    reason: str = Field(min_length=3, max_length=1000)


class FeedbackAccepted(BaseModel):
    feedback_id: str


class FeedbackSummary(BaseModel):
    total: int
    satisfactory: int
    unsatisfactory: int
    satisfaction_rate: Optional[float] = None
