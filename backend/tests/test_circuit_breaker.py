"""Tests for clarity_backend.utils.circuit_breaker."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from clarity_backend.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _ok() -> str:
    """Trivial coroutine that succeeds."""
    return "ok"


async def _fail() -> None:
    """Trivial coroutine that raises."""
    raise RuntimeError("boom")


def _make_breaker(threshold: int = 3, timeout: float = 60.0) -> CircuitBreaker:
    return CircuitBreaker("test", failure_threshold=threshold, reset_timeout=timeout)


# ---------------------------------------------------------------------------
# Constructor validation
# ---------------------------------------------------------------------------


def test_invalid_threshold_raises() -> None:
    with pytest.raises(ValueError, match="failure_threshold"):
        CircuitBreaker("bad", failure_threshold=0)


def test_invalid_timeout_raises() -> None:
    with pytest.raises(ValueError, match="reset_timeout"):
        CircuitBreaker("bad", reset_timeout=0.0)


# ---------------------------------------------------------------------------
# Normal operation (CLOSED state)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_closed_state_passes_call_through() -> None:
    breaker = _make_breaker()
    result = await breaker.call(_ok)
    assert result == "ok"
    assert breaker.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_single_failure_does_not_open() -> None:
    breaker = _make_breaker(threshold=3)
    with pytest.raises(RuntimeError):
        await breaker.call(_fail)
    assert breaker.state == CircuitState.CLOSED
    assert breaker._failure_count == 1


@pytest.mark.asyncio
async def test_success_resets_failure_count() -> None:
    breaker = _make_breaker(threshold=3)
    # Two consecutive failures …
    for _ in range(2):
        with pytest.raises(RuntimeError):
            await breaker.call(_fail)
    assert breaker._failure_count == 2
    # … followed by a success — counter must go back to zero.
    await breaker.call(_ok)
    assert breaker._failure_count == 0
    assert breaker.state == CircuitState.CLOSED


# ---------------------------------------------------------------------------
# Opens after N consecutive failures
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_opens_after_threshold_failures() -> None:
    breaker = _make_breaker(threshold=3)
    for _ in range(3):
        with pytest.raises(RuntimeError):
            await breaker.call(_fail)
    assert breaker.state == CircuitState.OPEN


@pytest.mark.asyncio
async def test_opens_exactly_at_threshold_not_before() -> None:
    breaker = _make_breaker(threshold=4)
    for i in range(4):
        with pytest.raises(RuntimeError):
            await breaker.call(_fail)
        expected = CircuitState.OPEN if i == 3 else CircuitState.CLOSED
        assert breaker.state == expected, f"Wrong state after failure {i + 1}"


# ---------------------------------------------------------------------------
# Rejects calls when OPEN
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_open_circuit_raises_circuit_open_error() -> None:
    breaker = _make_breaker(threshold=1, timeout=999.0)
    with pytest.raises(RuntimeError):
        await breaker.call(_fail)
    assert breaker.state == CircuitState.OPEN

    with pytest.raises(CircuitOpenError) as exc_info:
        await breaker.call(_ok)  # must not reach _ok

    assert exc_info.value.name == "test"


@pytest.mark.asyncio
async def test_open_circuit_does_not_call_underlying_function() -> None:
    breaker = _make_breaker(threshold=1, timeout=999.0)
    spy = AsyncMock(side_effect=RuntimeError("trip"))
    with pytest.raises(RuntimeError):
        await breaker.call(spy)

    spy2 = AsyncMock(return_value="should not run")
    with pytest.raises(CircuitOpenError):
        await breaker.call(spy2)

    spy2.assert_not_called()


# ---------------------------------------------------------------------------
# Resets after timeout (OPEN → HALF_OPEN)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transitions_to_half_open_after_timeout() -> None:
    breaker = _make_breaker(threshold=1, timeout=0.05)
    with pytest.raises(RuntimeError):
        await breaker.call(_fail)
    assert breaker.state == CircuitState.OPEN

    # Before timeout elapses — still OPEN.
    with pytest.raises(CircuitOpenError):
        await breaker.call(_ok)

    await asyncio.sleep(0.1)

    # After timeout — probe call should be attempted (HALF_OPEN).
    # _ok succeeds, so breaker should close again.
    result = await breaker.call(_ok)
    assert result == "ok"
    assert breaker.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_half_open_failure_reopens_circuit() -> None:
    breaker = _make_breaker(threshold=1, timeout=0.05)
    with pytest.raises(RuntimeError):
        await breaker.call(_fail)
    assert breaker.state == CircuitState.OPEN

    await asyncio.sleep(0.1)

    # Probe call fails → must return to OPEN.
    with pytest.raises(RuntimeError):
        await breaker.call(_fail)
    assert breaker.state == CircuitState.OPEN


# ---------------------------------------------------------------------------
# HALF_OPEN → CLOSED on success
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_half_open_success_closes_and_resets_counters() -> None:
    breaker = _make_breaker(threshold=2, timeout=0.05)
    for _ in range(2):
        with pytest.raises(RuntimeError):
            await breaker.call(_fail)
    assert breaker.state == CircuitState.OPEN

    await asyncio.sleep(0.1)

    await breaker.call(_ok)
    assert breaker.state == CircuitState.CLOSED
    assert breaker._failure_count == 0
    assert breaker._opened_at is None


# ---------------------------------------------------------------------------
# State transition logging
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_state_transitions_are_printed(capsys: pytest.CaptureFixture) -> None:
    breaker = _make_breaker(threshold=1, timeout=0.05)
    with pytest.raises(RuntimeError):
        await breaker.call(_fail)

    await asyncio.sleep(0.1)
    await breaker.call(_ok)

    captured = capsys.readouterr().out
    assert "[CircuitBreaker:test] CLOSED → OPEN" in captured
    assert "[CircuitBreaker:test] OPEN → HALF_OPEN" in captured
    assert "[CircuitBreaker:test] HALF_OPEN → CLOSED" in captured


# ---------------------------------------------------------------------------
# Concurrency — lock prevents race conditions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_concurrent_calls_do_not_corrupt_state() -> None:
    """Multiple coroutines failing simultaneously must not over-count."""
    breaker = _make_breaker(threshold=5, timeout=999.0)

    async def _slow_fail() -> None:
        await asyncio.sleep(0.01)
        raise RuntimeError("concurrent failure")

    tasks = [asyncio.create_task(breaker.call(_slow_fail)) for _ in range(5)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    assert all(isinstance(r, RuntimeError) for r in results)
    # The breaker must be OPEN — all five failures were counted without corruption.
    assert breaker.state == CircuitState.OPEN
    # Failure count equals the number of tasks (no double-counting under the lock).
    assert breaker._failure_count == 5


# ---------------------------------------------------------------------------
# CircuitOpenError message
# ---------------------------------------------------------------------------


def test_circuit_open_error_message_contains_name() -> None:
    err = CircuitOpenError("my-svc")
    assert "my-svc" in str(err)
    assert err.name == "my-svc"


# ---------------------------------------------------------------------------
# Integration: clarity client wraps errors as ClarityOfflineError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clarity_client_raises_offline_error_when_circuit_open() -> None:
    """When the module-level breaker is OPEN, _get/_post must raise ClarityOfflineError."""
    from clarity_backend.integrations import clarity as clarity_module
    from clarity_backend.integrations.clarity import ClarityClient, ClarityOfflineError

    client = ClarityClient(base_url="http://localhost:9999", api_key="test-key")

    # Force the module-level breaker into OPEN state without network calls.
    open_breaker = CircuitBreaker("clarity-app", failure_threshold=1, reset_timeout=999.0)
    # Trip it by recording a failure directly.
    async with open_breaker._lock:
        import time
        open_breaker._failure_count = 1
        open_breaker._opened_at = time.monotonic()
        open_breaker._transition(CircuitState.OPEN)

    with patch.object(clarity_module, "_clarity_breaker", open_breaker):
        with pytest.raises(ClarityOfflineError, match="circuit is open"):
            await client._get("/some/path")

        with pytest.raises(ClarityOfflineError, match="circuit is open"):
            await client._post("/some/path", json={"key": "val"})
