"""Tests for POST /webhooks/posthog."""

import pytest
from httpx import AsyncClient

from clarity_backend.triage import (
    classify_posthog_severity,
    make_posthog_fingerprint,
)


# ---------------------------------------------------------------------------
# Unit tests for triage helpers
# ---------------------------------------------------------------------------


class TestClassifyPosthogSeverity:
    def test_explicit_error_level(self):
        event = {"properties": {"$level": "error"}}
        assert classify_posthog_severity(event) == "high"

    def test_explicit_critical_level(self):
        event = {"properties": {"$level": "critical"}}
        assert classify_posthog_severity(event) == "critical"

    def test_warning_level(self):
        event = {"properties": {"$level": "warning"}}
        assert classify_posthog_severity(event) == "medium"

    def test_exception_type_keyword(self):
        event = {"properties": {"$exception_type": "TypeError"}}
        assert classify_posthog_severity(event) == "high"

    def test_oom_message_is_critical(self):
        event = {"properties": {"$exception_message": "process ran out of memory (OOM)"}}
        assert classify_posthog_severity(event) == "critical"

    def test_default_low(self):
        event = {"properties": {}}
        assert classify_posthog_severity(event) == "low"


class TestMakePosthogFingerprint:
    def test_same_event_same_fingerprint(self):
        event = {
            "event": "$exception",
            "distinct_id": "user-1",
            "properties": {
                "$exception_type": "TypeError",
                "$exception_message": "Cannot read property 'x' of undefined",
            },
        }
        assert make_posthog_fingerprint(event) == make_posthog_fingerprint(event)

    def test_different_message_different_fingerprint(self):
        base = {
            "event": "$exception",
            "distinct_id": "user-1",
            "properties": {"$exception_type": "TypeError", "$exception_message": "msg-a"},
        }
        other = {
            "event": "$exception",
            "distinct_id": "user-1",
            "properties": {"$exception_type": "TypeError", "$exception_message": "msg-b"},
        }
        assert make_posthog_fingerprint(base) != make_posthog_fingerprint(other)

    def test_returns_hex_string(self):
        event = {"event": "test", "properties": {}}
        fp = make_posthog_fingerprint(event)
        assert len(fp) == 64
        int(fp, 16)  # must be valid hex


# ---------------------------------------------------------------------------
# Integration tests against the FastAPI app
# ---------------------------------------------------------------------------

SAMPLE_EVENT = {
    "event": "$exception",
    "distinct_id": "user-42",
    "properties": {
        "$exception_type": "TypeError",
        "$exception_message": "Cannot read property 'foo' of undefined",
        "$current_url": "https://example.com/dashboard",
        "$browser": "Chrome",
        "$os": "Mac OS X",
    },
}


@pytest.mark.asyncio
async def test_posthog_webhook_creates_triage_item(client: AsyncClient):
    resp = await client.post("/webhooks/posthog", json=SAMPLE_EVENT)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ingested"] == 1
    assert data["updated"] == 0


@pytest.mark.asyncio
async def test_posthog_webhook_deduplicates_on_repeat(client: AsyncClient):
    await client.post("/webhooks/posthog", json=SAMPLE_EVENT)
    resp = await client.post("/webhooks/posthog", json=SAMPLE_EVENT)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ingested"] == 0
    assert data["updated"] == 1


@pytest.mark.asyncio
async def test_posthog_webhook_batch(client: AsyncClient):
    event_a = {**SAMPLE_EVENT, "distinct_id": "user-a"}
    event_b = {
        "event": "$exception",
        "distinct_id": "user-b",
        "properties": {"$exception_type": "RangeError", "$exception_message": "stack overflow"},
    }
    resp = await client.post("/webhooks/posthog", json={"batch": [event_a, event_b]})
    assert resp.status_code == 200
    assert resp.json()["ingested"] == 2


@pytest.mark.asyncio
async def test_posthog_webhook_severity_classified(client: AsyncClient):
    critical_event = {
        "event": "$exception",
        "distinct_id": "user-oom",
        "properties": {"$exception_message": "process ran out of memory OOM"},
    }
    resp = await client.post("/webhooks/posthog", json=critical_event)
    assert resp.status_code == 200
    assert resp.json()["ingested"] == 1
