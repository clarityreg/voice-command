import uuid
from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class TriageItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    source: str
    title: str
    description: str = ""
    severity: str = "low"  # low/medium/high/critical
    status: str = "pending"  # pending/snoozed/dismissed/actioned
    fingerprint: str = ""
    occurrence_count: int = 1
    first_seen: datetime = Field(default_factory=utcnow)
    last_seen: datetime = Field(default_factory=utcnow)
    metadata_json: str = "{}"  # JSON string for flexible metadata


class NotificationRecord(SQLModel, table=True):
    """Persistent store for notifications from Gmail, Slack, Outlook, Asana, Plane."""

    __tablename__ = "notifications"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    source: str = Field(max_length=20, index=True)
    source_account: str = Field(max_length=100)
    source_id: str = Field(max_length=200, index=True)
    notification_type: str = Field(max_length=20)
    title: str = Field(max_length=500)
    body: str = ""
    sender_name: str = Field(max_length=200)
    sender_avatar: str | None = Field(default=None, max_length=500)
    timestamp: datetime = Field(default_factory=utcnow)
    priority: str = Field(default="normal", max_length=10)
    triage_status: str = Field(default="unread", max_length=10, index=True)
    is_actionable: bool = True
    thread_id: str | None = Field(default=None, max_length=200)
    channel_name: str | None = Field(default=None, max_length=200)
    project_name: str | None = Field(default=None, max_length=200)
    snoozed_until: datetime | None = None
    raw_payload: str | None = None  # JSON string
    created_at: datetime = Field(default_factory=utcnow)


class TokenStore(SQLModel, table=True):
    """Store OAuth tokens for Gmail and Outlook accounts."""

    __tablename__ = "tokens"

    id: str = Field(max_length=100, primary_key=True)  # e.g. "gmail:user@email.com"
    service: str = Field(max_length=20)
    account: str = Field(max_length=100)
    access_token: str
    refresh_token: str | None = None
    expires_at: datetime | None = None
    extra_data: str | None = None
