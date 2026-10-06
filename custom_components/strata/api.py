"""Small async client for the Strata server (OpenAI compatible, plus status)."""

from __future__ import annotations

import asyncio
import json as json_module
from typing import Any

import aiohttp


class StrataError(Exception):
    """Base error."""


class StrataConnectionError(StrataError):
    """The server cannot be reached."""


class StrataAuthError(StrataError):
    """The API key is missing or wrong."""


class StrataBusyError(StrataError):
    """The server refused because it is busy (HTTP 409/503)."""


class StrataClient:
    """Talk to one Strata server."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int,
        api_key: str | None = None,
        ssl: bool = False,
    ) -> None:
        self._session = session
        self._base = f"{'https' if ssl else 'http'}://{host}:{port}"
        self._headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    @property
    def base_url(self) -> str:
        return self._base

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        timeout: float = 15,
    ) -> Any:
        try:
            async with self._session.request(
                method,
                f"{self._base}{path}",
                json=json,
                headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                if resp.status in (401, 403):
                    raise StrataAuthError("Invalid API key")
                if resp.status in (409, 503):
                    raise StrataBusyError(await resp.text())
                if resp.status >= 400:
                    raise StrataError(f"HTTP {resp.status}: {(await resp.text())[:300]}")
                text = await resp.text()
                try:
                    return json_module.loads(text)
                except ValueError:
                    return text
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise StrataConnectionError(str(err) or type(err).__name__) from err

    async def health(self) -> dict[str, Any]:
        """GET /health (no key needed)."""
        return await self._request("GET", "/health")

    async def status(self) -> dict[str, Any]:
        """GET /v1/status (key needed when one is set)."""
        return await self._request("GET", "/v1/status")

    async def metrics(self) -> dict[str, Any]:
        """GET /metrics: live state and hardware."""
        return await self._request("GET", "/metrics")

    async def models(self) -> list[str]:
        data = await self._request("GET", "/v1/models")
        return [m["id"] for m in data.get("data", [])]

    async def load(self) -> None:
        await self._request("POST", "/v1/load", json={}, timeout=300)

    async def unload(self) -> None:
        await self._request("POST", "/v1/unload", json={})

    async def chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST /v1/chat/completions (non-streaming)."""
        return await self._request(
            "POST", "/v1/chat/completions", json=payload, timeout=300
        )
