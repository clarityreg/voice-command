import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from clarity_backend.models import utcnow


class AgentJob(SQLModel, table=True):
    __tablename__ = "agentjob"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    triage_item_id: int
    status: str = "planning"  # planning, plan_ready, approved, running, completed, failed, cancelled
    plan_text: str | None = None
    result_summary: str | None = None
    branch_name: str | None = None
    error_message: str | None = None
    events_json: str = "[]"
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
