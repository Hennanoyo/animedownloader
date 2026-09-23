from collections.abc import Sequence
from types import TracebackType
from typing import Self, cast

import httpx
from animedownloader_torrent import TorrentInfo, TorrentStatus

from .exceptions import (
    QBittorrentAddError,
    QBittorrentAPIError,
    QBittorrentAuthenticationError,
    QBittorrentConnectionError,
)

API_PREFIX = "/api/v2"
USER_AGENT = "AnimeDownloader/0.1"

_STATE_MAP = {
    "downloading": TorrentStatus.DOWNLOADING,
    "forcedDL": TorrentStatus.DOWNLOADING,
    "stalledDL": TorrentStatus.STALLED,
    "pausedDL": TorrentStatus.PAUSED,
    "queuedDL": TorrentStatus.QUEUED,
    "checkingDL": TorrentStatus.CHECKING,
    "checkingResumeData": TorrentStatus.CHECKING,
    "uploading": TorrentStatus.SEEDING,
    "forcedUP": TorrentStatus.SEEDING,
    "stalledUP": TorrentStatus.SEEDING,
    "pausedUP": TorrentStatus.PAUSED,
    "queuedUP": TorrentStatus.QUEUED,
    "checkingUP": TorrentStatus.CHECKING,
    "moving": TorrentStatus.MOVING,
    "error": TorrentStatus.ERROR,
    "missingFiles": TorrentStatus.ERROR,
    "allocating": TorrentStatus.CHECKING,
}


class QBittorrentClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        timeout: float = 10.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/") + API_PREFIX
        self._api_key = api_key
        self._timeout = timeout
        self._http_client = http_client
        self._owns_client = http_client is None

    async def __aenter__(self) -> Self:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=httpx.Timeout(self._timeout, connect=5.0),
                follow_redirects=True,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json",
                },
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

    async def add(
        self,
        source: str,
        *,
        save_path: str,
        tags: Sequence[str] = (),
    ) -> None:
        data: dict[str, str] = {
            "urls": source,
            "savepath": save_path,
            "autoTMM": "false",
        }
        normalized_tags = [tag for tag in tags if tag]
        if normalized_tags:
            data["tags"] = ",".join(normalized_tags)

        response = await self._request("POST", "/torrents/add", data=data)
        body = response.text.strip().lower()
        if body not in {"", "ok."}:
            raise QBittorrentAddError(
                f"qBittorrent rejected torrent add request: {response.text.strip()}"
            )

    async def get(self, torrent_id: str) -> TorrentInfo | None:
        response = await self._request(
            "GET",
            "/torrents/info",
            params={"hashes": torrent_id, "limit": "1"},
        )
        torrents = self._decode_torrent_list(response)
        if not torrents:
            return None
        return self._parse_torrent(torrents[0])

    async def find_by_tag(self, tag: str) -> TorrentInfo | None:
        response = await self._request(
            "GET",
            "/torrents/info",
            params={
                "tag": tag,
                "sort": "added_on",
                "reverse": "true",
                "limit": "1",
            },
        )
        torrents = self._decode_torrent_list(response)
        if not torrents:
            return None
        return self._parse_torrent(torrents[0])

    async def remove(
        self,
        torrent_id: str,
        *,
        delete_files: bool = False,
    ) -> None:
        await self._request(
            "POST",
            "/torrents/delete",
            data={
                "hashes": torrent_id,
                "deleteFiles": "true" if delete_files else "false",
            },
        )

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: object,
    ) -> httpx.Response:
        if self._http_client is None:
            raise RuntimeError(
                "QBittorrentClient must be used as an async context manager"
            )

        try:
            response = await self._http_client.request(method, path, **kwargs)
        except httpx.RequestError as exc:
            raise QBittorrentConnectionError(
                "qBittorrent API request failed"
            ) from exc

        if response.status_code in {401, 403}:
            raise QBittorrentAuthenticationError(
                f"qBittorrent authentication failed with HTTP {response.status_code}"
            )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise QBittorrentAPIError(
                f"qBittorrent API request failed with HTTP {response.status_code}"
            ) from exc

        return response

    @staticmethod
    def _decode_torrent_list(response: httpx.Response) -> list[dict[str, object]]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise QBittorrentAPIError("qBittorrent returned invalid JSON") from exc

        if not isinstance(payload, list):
            raise QBittorrentAPIError("qBittorrent returned an invalid torrent list")

        torrents: list[dict[str, object]] = []
        for item in payload:
            if not isinstance(item, dict):
                raise QBittorrentAPIError("qBittorrent returned an invalid torrent item")
            torrents.append(cast(dict[str, object], item))
        return torrents

    @classmethod
    def _parse_torrent(cls, payload: dict[str, object]) -> TorrentInfo:
        torrent_id = cls._require_string(payload, "hash")
        name = cls._require_string(payload, "name")
        state = cls._require_string(payload, "state")

        progress = cls._require_float(payload, "progress")
        downloaded_bytes = cls._require_int(payload, "completed")
        total_bytes = cls._require_int(payload, "size")
        save_path = cls._require_string(payload, "save_path")
        tags = frozenset(
            tag.strip()
            for tag in cls._require_string(payload, "tags").split(",")
            if tag.strip()
        )

        return TorrentInfo(
            id=torrent_id,
            name=name,
            status=_STATE_MAP.get(state, TorrentStatus.UNKNOWN),
            progress=progress,
            downloaded_bytes=downloaded_bytes,
            total_bytes=total_bytes,
            save_path=save_path,
            tags=tags,
        )

    @staticmethod
    def _require_string(payload: dict[str, object], field: str) -> str:
        value = payload.get(field)
        if not isinstance(value, str):
            raise QBittorrentAPIError(
                f"qBittorrent torrent field '{field}' is missing or invalid"
            )
        return value

    @staticmethod
    def _require_int(payload: dict[str, object], field: str) -> int:
        value = payload.get(field)
        if isinstance(value, bool) or not isinstance(value, int):
            raise QBittorrentAPIError(
                f"qBittorrent torrent field '{field}' is missing or invalid"
            )
        return value

    @staticmethod
    def _require_float(payload: dict[str, object], field: str) -> float:
        value = payload.get(field)
        if isinstance(value, bool) or not isinstance(value, (float, int)):
            raise QBittorrentAPIError(
                f"qBittorrent torrent field '{field}' is missing or invalid"
            )
        return float(value)
