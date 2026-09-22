from collections.abc import AsyncIterator
from types import TracebackType
from typing import Self

import httpx

from animedownloader_releases import Release
from defusedxml import ElementTree

from .parser import parse_rss_feed

DEFAULT_BASE_URL = "https://nyaa.si"
USER_AGENT = "AnimeDownloader/0.1"


class NyaaError(RuntimeError):
    """Base exception for Nyaa client failures."""


class NyaaUpstreamError(NyaaError):
    """The Nyaa RSS endpoint could not be reached successfully."""


class NyaaParseError(NyaaError):
    """The Nyaa RSS response could not be parsed."""


class NyaaClient:
    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 10.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._http_client = http_client
        self._owns_client = http_client is None

    async def __aenter__(self) -> Self:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=httpx.Timeout(self._timeout, connect=5.0),
                follow_redirects=True,
                headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml"},
            )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._owns_client and self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def search(self, query: str) -> list[Release]:
        if self._http_client is None:
            raise RuntimeError("NyaaClient must be used as an async context manager")

        try:
            response = await self._http_client.get(
                "/",
                params={"page": "rss", "q": query},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise NyaaUpstreamError("Nyaa RSS request failed") from exc

        try:
            return parse_rss_feed(response.text)
        except (ElementTree.ParseError, ValueError) as exc:
            raise NyaaParseError("Nyaa RSS response is invalid") from exc


async def stream_search(client: NyaaClient, query: str) -> AsyncIterator[Release]:
    for release in await client.search(query):
        yield release
