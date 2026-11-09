from sqlalchemy import func, select

from app.database import SessionLocal
from app.models import Feedback, Run
from app.schemas import FeedbackSummary


def save_feedback(feedback):
    with SessionLocal() as session:
        if session.get(Run, feedback.run_id) is None:
            return None
        record = Feedback(
            run_id=feedback.run_id,
            satisfactory=feedback.satisfactory,
            reason=feedback.reason,
        )
        session.add(record)
        session.commit()
        return record.id


def feedback_summary():
    with SessionLocal() as session:
        total = session.scalar(select(func.count()).select_from(Feedback))
        satisfactory = session.scalar(
            select(func.count()).select_from(Feedback).where(Feedback.satisfactory.is_(True))
        )
    return FeedbackSummary(
        total=total,
        satisfactory=satisfactory,
        unsatisfactory=total - satisfactory,
        satisfaction_rate=round(satisfactory / total, 4) if total else None,
    )
