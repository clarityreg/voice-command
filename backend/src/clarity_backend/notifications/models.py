import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class Source(StrEnum):
    GMAIL = "gmail"
    OUTLOOK = "outlook"
    SLACK = "slack"
    ASANA = "asana"
    PLANE = "plane"
    POSTHOG = "posthog"


class NotificationType(StrEnum):
    EMAIL = "email"
    MESSAGE = "message"
    TASK_UPDATE = "task_update"
    TASK_ASSIGNED = "task_assigned"
    MENTION = "mention"
    COMMENT = "comment"
    REMINDER = "reminder"


class Priority(StrEnum):
    URGENT = "urgent"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class TriageStatus(StrEnum):
    UNREAD = "unread"
    READ = "read"
    SNOOZED = "snoozed"
    ARCHIVED = "archived"
    ACTIONED = "actioned"


class Notification(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: Source
    source_account: str
    source_id: str
    notification_type: NotificationType
    title: str
    body: str
    sender_name: str
    sender_avatar: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    priority: Priority = Priority.NORMAL
    triage_status: TriageStatus = TriageStatus.UNREAD
    is_actionable: bool = True
    thread_id: str | None = None
    channel_name: str | None = None
    project_name: str | None = None
    snoozed_until: datetime | None = None
    raw_payload: dict | None = None


class NotificationAction(BaseModel):
    notification_id: str
    action: Literal[
        "reply", "archive", "snooze", "mark_read",
        "actioned", "create_task", "open_in_app",
    ]
    payload: dict | None = None


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    target: Literal["plane", "asana"]
    priority: Priority = Priority.NORMAL
    project_id: str | None = None
    source_notification_id: str | None = None


class WebSocketMessage(BaseModel):
    event: Literal[
        "new_notification", "notification_updated", "notification_removed",
        "connection_status", "error", "initial_load",
        "agent_job_created", "agent_progress", "agent_plan_ready",
        "agent_job_updated", "agent_completed", "agent_failed",
    ]
    data: dict
