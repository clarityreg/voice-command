"""Clarity App API client — calls the Django regulatory platform over HTTP."""

import httpx

from clarity_backend.utils.circuit_breaker import CircuitBreaker, CircuitOpenError

# Module-level circuit breaker shared by all ClarityClient instances.
# Opens after 3 consecutive network-level failures; resets after 60 s.
_clarity_breaker: CircuitBreaker = CircuitBreaker(
    "clarity-app",
    failure_threshold=3,
    reset_timeout=60.0,
)


class ClarityOfflineError(Exception):
    """Raised when the Clarity App is unreachable."""


class ClarityClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    @property
    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": self.api_key, "Content-Type": "application/json"}

    async def _get(self, path: str, params: dict | None = None) -> dict:
        async def _do_get() -> dict:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(
                        f"{self.base_url}/{path.lstrip('/')}",
                        headers=self._headers,
                        params=params,
                    )
                    resp.raise_for_status()
                    return resp.json()
            except (httpx.ConnectError, httpx.ConnectTimeout) as e:
                raise ClarityOfflineError(str(e)) from e

        try:
            return await _clarity_breaker.call(_do_get)
        except CircuitOpenError as e:
            raise ClarityOfflineError(
                f"Clarity App circuit is open — too many recent failures. ({e})"
            ) from e

    async def _post(self, path: str, json: dict | None = None) -> dict:
        async def _do_post() -> dict:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        f"{self.base_url}/{path.lstrip('/')}",
                        headers=self._headers,
                        json=json or {},
                    )
                    resp.raise_for_status()
                    return resp.json()
            except (httpx.ConnectError, httpx.ConnectTimeout) as e:
                raise ClarityOfflineError(str(e)) from e

        try:
            return await _clarity_breaker.call(_do_post)
        except CircuitOpenError as e:
            raise ClarityOfflineError(
                f"Clarity App circuit is open — too many recent failures. ({e})"
            ) from e

    # --- Schedule & Compliance ---

    async def get_schedule_dashboard(self, client_id: str = "default") -> dict:
        return await self._get(f"api/schedules/{client_id}/dashboard/")

    async def get_compliance_summary(self, client_id: str = "default") -> dict:
        return await self._get(f"api/schedules/{client_id}/compliance/summary/")

    # --- ADHD Bridge ---

    async def get_unified_inbox(self) -> dict:
        return await self._get("api/adhd/unified-inbox/")

    async def create_parking_lot_item(self, content: str) -> dict:
        return await self._post("api/adhd/parking-lot/", json={"content": content})

    async def start_blitz(self) -> dict:
        return await self._post("api/adhd/blitz/")

    async def get_gamification_profile(self) -> dict:
        return await self._get("api/adhd/gamification/profile/")

    # --- Email ---

    async def get_upcoming_actions(self) -> dict:
        return await self._get("api/email/action-points/upcoming/")

    async def start_email_review(self) -> dict:
        return await self._post("api/email/review/start/")

    async def get_email_analytics(self) -> dict:
        return await self._get("api/email/analytics/")

    # --- Reviews & RAG ---

    async def check_compliance(self, ingredient: str, market: str | None = None) -> dict:
        body: dict = {"ingredient": ingredient}
        if market:
            body["market"] = market
        return await self._post("api/reviews/compliance-check/", json=body)

    async def rag_query(self, query: str) -> dict:
        return await self._post("api/rag/query/", json={"query": query})


def _get_clarity_client() -> ClarityClient:
    """Build a ClarityClient from settings + env vars."""
    from clarity_backend.config import settings as env_settings
    from clarity_backend.settings.manager import _read_settings

    s = _read_settings()
    base_url = s.get("clarity_api_url") or env_settings.CLARITY_API_URL
    api_key = s.get("clarity_api_key") or env_settings.CLARITY_API_KEY
    return ClarityClient(base_url=base_url, api_key=api_key)
