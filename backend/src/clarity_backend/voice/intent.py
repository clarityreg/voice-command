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
UNKNOWN = "unknown"

# Keyword patterns mapped to intents (first match wins)
INTENT_PATTERNS: list[tuple[str, str]] = [
    (r"(fix|patch|repair|resolve|auto.?fix).+(item|error|issue|vuln|#?\d+)", FIX_ITEM),
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

    return params
