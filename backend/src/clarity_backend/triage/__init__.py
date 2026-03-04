"""Triage helper utilities for classifying and fingerprinting PostHog events."""

import hashlib
import json

_CRITICAL_KEYWORDS = {"oom", "out of memory", "fatal", "crash"}
_HIGH_TYPE_KEYWORDS = {"typeerror", "referenceerror", "syntaxerror", "rangeerror"}

_LEVEL_MAP = {
    "critical": "critical",
    "error": "high",
    "warning": "medium",
    "warn": "medium",
    "info": "low",
    "debug": "low",
}


def classify_posthog_severity(event: dict) -> str:
    props = event.get("properties", {})

    level = props.get("$level", "").lower()
    if level in _LEVEL_MAP:
        return _LEVEL_MAP[level]

    msg = props.get("$exception_message", "").lower()
    if any(kw in msg for kw in _CRITICAL_KEYWORDS):
        return "critical"

    exc_type = props.get("$exception_type", "").lower()
    if exc_type in _HIGH_TYPE_KEYWORDS:
        return "high"

    return "low"


def make_posthog_fingerprint(event: dict) -> str:
    props = event.get("properties", {})
    exception_type = props.get("$exception_type", "UnknownError")
    exception_message = props.get("$exception_message", "")
    raw = f"{exception_type}{exception_message}posthog"
    return hashlib.sha256(raw.encode()).hexdigest()


def extract_posthog_title(event: dict) -> str:
    props = event.get("properties", {})
    exception_type = props.get("$exception_type", "UnknownError")
    exception_message = props.get("$exception_message", "")
    return f"{exception_type}: {exception_message}"[:255]


def safe_metadata(event: dict) -> str:
    props = event.get("properties", {})
    return json.dumps(
        {
            "distinct_id": event.get("distinct_id"),
            "timestamp": event.get("timestamp"),
            "exception_list": props.get("$exception_list", []),
            "current_url": props.get("$current_url", ""),
        }
    )
