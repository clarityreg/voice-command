"""Intent classification for voice/text commands.

Uses keyword matching as the primary classifier. Fast, offline, fully testable.
Claude CLI subprocess can optionally enhance responses for ambiguous inputs.
"""

import re
from dataclasses import dataclass

# Intent types
QUERY_ERRORS = "query_errors"
QUERY_VULNS = "query_vulns"
CHECK_STATUS = "check_status"
CREATE_ISSUE = "create_issue"
SNOOZE_ITEM = "snooze_item"
DISMISS_ITEM = "dismiss_item"
MORNING_BRIEF = "morning_brief"
READ_EMAILS = "read_emails"
READ_NOTIFICATIONS = "read_notifications"
REPLY_MESSAGE = "reply_message"
ARCHIVE_NOTIFICATION = "archive_notification"
FIX_ITEM = "fix_item"
PLANE_CREATE_TASK = "plane_create_task"
PLANE_COMPLETE_TASK = "plane_complete_task"
PLANE_LIST_TASKS = "plane_list_tasks"
UNKNOWN = "unknown"

# Keyword patterns mapped to intents (first match wins)
# NOTE: Plane task patterns must come BEFORE generic CREATE_ISSUE to avoid conflicts
INTENT_PATTERNS: list[tuple[str, str]] = [
    (r"(fix|patch|repair|resolve|auto.?fix).+(item|error|issue|vuln|#?\d+)", FIX_ITEM),
    # Plane: "create a task in acme: update docs" / "add a ticket to client-x fix bug"
    # Handles: articles (a/an), prepositions (in/for/to), verbs (create/add/new/make)
    (r"(create|add|new|make)\s+(a\s+)?(urgent\s+|high\s+|medium\s+|low\s+)?(task|work item|ticket)\s+(in|for|to)\s+", PLANE_CREATE_TASK),
    # Plane: "complete task ACME-42" / "done with task 5" / "mark task acme-15 as done"
    (r"(complete|finish|done|close|resolve|mark)\s+(with\s+)?(task|ticket|item)\s+", PLANE_COMPLETE_TASK),
    # Plane: "show my tasks" / "list tasks in acme" / "what are my tickets"
    (r"(show|list|what are|check)\s+(my\s+)?(tasks|work items|tickets)", PLANE_LIST_TASKS),
    (r"\b(error|errors|exception|crash|bug|bugs|fail|failing)\b", QUERY_ERRORS),
    (r"\b(vuln|vulnerability|vulnerabilities|security|cve)\b", QUERY_VULNS),
    (r"\b(status|overview|summary|how.+things|what.+going on)\b", CHECK_STATUS),
    (r"\b(email|emails|inbox|gmail|outlook|mail)\b", READ_EMAILS),
    (r"\b(notification|notifications|messages|unread)\b", READ_NOTIFICATIONS),
    (r"\b(reply|respond|answer)\b", REPLY_MESSAGE),
    (r"\b(archive)\b.+(notification|email|message|all)", ARCHIVE_NOTIFICATION),
    (r"\b(create|open|file|make).+(issue|ticket|task|item)\b", CREATE_ISSUE),
    (r"\b(snooze|delay|postpone|later|remind)\b", SNOOZE_ITEM),
    (r"\b(dismiss|ignore|skip|close)\b", DISMISS_ITEM),
    (r"\b(brief|morning|overnight|digest|recap)\b", MORNING_BRIEF),
]


@dataclass
class Intent:
    type: str
    confidence: float
    params: dict

    def to_dict(self) -> dict:
        return {"type": self.type, "confidence": self.confidence, "params": self.params}


def classify(text: str) -> Intent:
    """Classify text into an intent using keyword matching."""
    lower = text.lower().strip()

    if not lower:
        return Intent(type=UNKNOWN, confidence=0.0, params={})

    for pattern, intent_type in INTENT_PATTERNS:
        if re.search(pattern, lower):
            return Intent(type=intent_type, confidence=0.85, params=_extract_params(lower, intent_type))

    return Intent(type=UNKNOWN, confidence=0.0, params={"original_text": text})


def _extract_params(text: str, intent_type: str) -> dict:
    """Extract parameters from the text based on intent type."""
    params: dict = {}

    if intent_type in (QUERY_ERRORS, QUERY_VULNS):
        if "today" in text or "24" in text:
            params["timeframe"] = "24h"
        elif "week" in text:
            params["timeframe"] = "7d"
        elif "yesterday" in text:
            params["timeframe"] = "yesterday"

        # Try to extract severity
        for sev in ("critical", "high", "medium", "low"):
            if sev in text:
                params["severity"] = sev
                break

    elif intent_type == CREATE_ISSUE:
        # Try to extract item ID reference
        id_match = re.search(r"#?(\d+)", text)
        if id_match:
            params["item_id"] = int(id_match.group(1))

    elif intent_type in (SNOOZE_ITEM, DISMISS_ITEM, FIX_ITEM):
        id_match = re.search(r"#?(\d+)", text)
        if id_match:
            params["item_id"] = int(id_match.group(1))

    elif intent_type == PLANE_CREATE_TASK:
        # Extract: "create [priority] task in <project>[: <title>]"
        # Also handles voice without colon: "create task in acme update docs"
        for prio in ("urgent", "high", "medium", "low"):
            if prio in text:
                params["priority"] = prio
                break

        # Find the project name and title after "in/for/to <project>"
        # Prefer "in/for" over "to" to avoid false matches on "I want to create..."
        # Use word boundaries to prevent matching "login", "information", etc.
        m = re.search(r"\bin\b\s+(.+)", text) or re.search(r"\bfor\b\s+(.+)", text) or re.search(r"\b(?:task|ticket|work item)\s+to\s+(.+)", text)
        if m:
            rest = m.group(1).strip()
            # Split on colon, dash, or first word boundary after project name
            # Try colon/dash first
            parts = re.split(r"\s*[:\-]\s*", rest, maxsplit=1)
            if len(parts) == 2:
                params["project_name"] = parts[0].strip()
                params["task_title"] = parts[1].strip()
            else:
                # No colon — heuristic: first word(s) before a verb-like word is project
                # For simplicity, take first word as project, rest as title
                words = rest.split()
                if len(words) >= 2:
                    params["project_name"] = words[0]
                    params["task_title"] = " ".join(words[1:])
                else:
                    params["project_name"] = rest

    elif intent_type == PLANE_COMPLETE_TASK:
        # Extract: "complete task ACME-42" or "done with task 5" or "mark task acme-42 as done"
        m = re.search(r"(?:task|ticket|item)\s+(.+)", text)
        if m:
            ref = m.group(1).strip()
            # Strip trailing "as done/complete/finished"
            ref = re.sub(r"\s+as\s+(done|complete|finished)$", "", ref)
            params["task_ref"] = ref

    elif intent_type == PLANE_LIST_TASKS:
        # Extract optional project name: "show tasks in acme"
        m = re.search(r"(?:in|for)\s+(.+)", text)
        if m:
            params["project_name"] = m.group(1).strip()

    return params
