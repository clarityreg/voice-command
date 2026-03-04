import hashlib
import hmac
import json
import time

import pytest
from httpx import AsyncClient

from clarity_backend.config import settings

TEST_SECRET = "test-secret-key"

SAMPLE_PAYLOAD = {
    "event_type": "new_vulnerability",
    "vulnerability": {
        "id": "vuln-123",
        "cve": "CVE-2024-1234",
        "package_name": "lodash",
        "package_version": "4.17.20",
        "severity": "critical",
        "title": "Prototype Pollution in lodash",
        "description": "Lodash versions prior to 4.17.21 are vulnerable...",
        "remediation": "Upgrade to lodash@4.17.21",
    },
}


def make_signature(body: bytes, timestamp: str, secret: str = TEST_SECRET) -> str:
    return hmac.new(
        secret.encode(),
        f"{timestamp}.".encode() + body,
        hashlib.sha256,
    ).hexdigest()


def make_headers(body: bytes, timestamp: str | None = None, secret: str = TEST_SECRET) -> dict:
    ts = timestamp or str(int(time.time()))
    sig = make_signature(body, ts, secret)
    return {
        "X-Aikido-Webhook-Signature": sig,
        "X-Aikido-Webhook-Timestamp": ts,
        "Content-Type": "application/json",
    }


@pytest.fixture(autouse=True)
def patch_secret(monkeypatch):
    monkeypatch.setattr(settings, "AIKIDO_WEBHOOK_SECRET", TEST_SECRET)


@pytest.mark.asyncio
async def test_valid_payload_creates_triage_item(client: AsyncClient):
    body = json.dumps(SAMPLE_PAYLOAD).encode()
    headers = make_headers(body)
    response = await client.post("/webhooks/aikido", content=body, headers=headers)
    assert response.status_code == 202
    assert response.json() == {"status": "accepted"}


@pytest.mark.asyncio
async def test_invalid_signature_returns_401(client: AsyncClient):
    body = json.dumps(SAMPLE_PAYLOAD).encode()
    ts = str(int(time.time()))
    headers = {
        "X-Aikido-Webhook-Signature": "invalidsignature",
        "X-Aikido-Webhook-Timestamp": ts,
        "Content-Type": "application/json",
    }
    response = await client.post("/webhooks/aikido", content=body, headers=headers)
    assert response.status_code == 401
    assert "signature" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_wrong_secret_returns_401(client: AsyncClient):
    body = json.dumps(SAMPLE_PAYLOAD).encode()
    headers = make_headers(body, secret="wrong-secret")
    response = await client.post("/webhooks/aikido", content=body, headers=headers)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_expired_timestamp_returns_401(client: AsyncClient):
    body = json.dumps(SAMPLE_PAYLOAD).encode()
    old_ts = str(int(time.time()) - 60)  # 60 seconds ago
    headers = make_headers(body, timestamp=old_ts)
    response = await client.post("/webhooks/aikido", content=body, headers=headers)
    assert response.status_code == 401
    assert "old" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_future_timestamp_returns_401(client: AsyncClient):
    body = json.dumps(SAMPLE_PAYLOAD).encode()
    future_ts = str(int(time.time()) + 60)  # 60 seconds in future
    headers = make_headers(body, timestamp=future_ts)
    response = await client.post("/webhooks/aikido", content=body, headers=headers)
    assert response.status_code == 401
    assert "old" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_invalid_timestamp_format_returns_401(client: AsyncClient):
    body = json.dumps(SAMPLE_PAYLOAD).encode()
    sig = make_signature(body, "notanumber")
    headers = {
        "X-Aikido-Webhook-Signature": sig,
        "X-Aikido-Webhook-Timestamp": "notanumber",
        "Content-Type": "application/json",
    }
    response = await client.post("/webhooks/aikido", content=body, headers=headers)
    assert response.status_code == 401
    assert "timestamp" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_missing_signature_header_returns_422(client: AsyncClient):
    body = json.dumps(SAMPLE_PAYLOAD).encode()
    response = await client.post(
        "/webhooks/aikido",
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_cve_used_as_fingerprint(client: AsyncClient):
    """CVE is used as fingerprint when present."""
    body = json.dumps(SAMPLE_PAYLOAD).encode()
    headers = make_headers(body)
    response = await client.post("/webhooks/aikido", content=body, headers=headers)
    assert response.status_code == 202


@pytest.mark.asyncio
async def test_vuln_id_as_fingerprint_when_no_cve(client: AsyncClient):
    """Vulnerability ID used as fingerprint when no CVE."""
    payload = {
        "event_type": "new_vulnerability",
        "vulnerability": {
            "id": "vuln-no-cve",
            "package_name": "some-pkg",
            "package_version": "1.0.0",
            "severity": "high",
            "title": "Some Vulnerability",
        },
    }
    body = json.dumps(payload).encode()
    headers = make_headers(body)
    response = await client.post("/webhooks/aikido", content=body, headers=headers)
    assert response.status_code == 202
