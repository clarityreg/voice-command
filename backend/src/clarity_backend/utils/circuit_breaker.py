"""Async circuit breaker for guarding external service calls.

State machine
-------------
CLOSED   — normal operation; failures are counted.
OPEN     — threshold exceeded; all calls are rejected immediately.
HALF_OPEN — reset_timeout elapsed; one probe call is allowed through.
             Success  → CLOSED (counters reset).
             Failure  → OPEN   (timeout restarts).

Usage
-----
    breaker = CircuitBreaker("my-service", failure_threshold=3, reset_timeout=60.0)

    try:
        result = await breaker.call(some_async_func, arg1, kwarg=val)
    except CircuitOpenError:
        # fast-fail path
        ...
"""

from __future__ import annotations

import asyncio
import time
from enum import Enum, auto
from typing import Any, Callable, Coroutine


class CircuitState(Enum):
    CLOSED = auto()
    OPEN = auto()
    HALF_OPEN = auto()


class CircuitOpenError(Exception):
    """Raised when a call is attempted while the circuit is OPEN."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(
            f"Circuit breaker '{name}' is OPEN — call rejected. "
            "Wait for the reset timeout before retrying."
        )


class CircuitBreaker:
    """Thread-safe async circuit breaker.

    Parameters
    ----------
    name:
        Human-readable label used in log output.
    failure_threshold:
        Number of consecutive failures that trip the breaker (default 3).
    reset_timeout:
        Seconds to wait in the OPEN state before moving to HALF_OPEN (default 60).
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        reset_timeout: float = 60.0,
    ) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if reset_timeout <= 0:
            raise ValueError("reset_timeout must be > 0")

        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout

        self._state: CircuitState = CircuitState.CLOSED
        self._failure_count: int = 0
        self._opened_at: float | None = None
        self._lock: asyncio.Lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def state(self) -> CircuitState:
        return self._state

    async def call(
        self,
        func: Callable[..., Coroutine[Any, Any, Any]],
        /,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute *func* if the circuit permits; otherwise raise CircuitOpenError.

        Parameters
        ----------
        func:
            Async callable to invoke.
        *args, **kwargs:
            Forwarded verbatim to *func*.

        Returns
        -------
        Whatever *func* returns on success.

        Raises
        ------
        CircuitOpenError
            When the circuit is OPEN and the reset timeout has not elapsed.
        Any exception raised by *func*
            Propagated after recording the failure.
        """
        async with self._lock:
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._transition(CircuitState.HALF_OPEN)
                else:
                    raise CircuitOpenError(self.name)

        # Execute the probe / normal call outside the lock so we don't
        # block other coroutines for the duration of the network call.
        try:
            result = await func(*args, **kwargs)
        except Exception:
            async with self._lock:
                self._record_failure()
            raise

        async with self._lock:
            self._record_success()

        return result

    # ------------------------------------------------------------------
    # Internal helpers  (all called with self._lock held)
    # ------------------------------------------------------------------

    def _should_attempt_reset(self) -> bool:
        if self._opened_at is None:
            return False
        return (time.monotonic() - self._opened_at) >= self.reset_timeout

    def _record_failure(self) -> None:
        self._failure_count += 1
        if self._state == CircuitState.HALF_OPEN:
            # Probe failed — stay / return OPEN and restart the timeout.
            self._opened_at = time.monotonic()
            self._transition(CircuitState.OPEN)
        elif (
            self._state == CircuitState.CLOSED
            and self._failure_count >= self.failure_threshold
        ):
            self._opened_at = time.monotonic()
            self._transition(CircuitState.OPEN)

    def _record_success(self) -> None:
        if self._state in (CircuitState.HALF_OPEN, CircuitState.CLOSED):
            self._failure_count = 0
            self._opened_at = None
            if self._state != CircuitState.CLOSED:
                self._transition(CircuitState.CLOSED)

    def _transition(self, new_state: CircuitState) -> None:
        old_state = self._state
        self._state = new_state
        print(f"[CircuitBreaker:{self.name}] {old_state.name} → {new_state.name}")
