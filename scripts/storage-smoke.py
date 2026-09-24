#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import http.client
import sys
from pathlib import Path
from urllib.parse import quote, urlsplit
from tempfile import TemporaryDirectory
from uuid import uuid7

from animedownloader_config import Settings
from animedownloader_storage import StorageError, create_storage


async def main() -> int:
    settings = Settings()
    storage = create_storage(
        backend="seaweedfs",
        local_root=settings.media_root,
        internal_url=settings.storage_internal_url,
        public_url=settings.storage_public_url,
    )
    key = f"smoke/storage/{uuid7()}.txt"

    with TemporaryDirectory(prefix="animedownloader-storage-smoke-") as directory:
        root = Path(directory)
        source = root / "source.txt"
        destination = root / "destination.txt"
        source.write_text("animedownloader storage smoke", encoding="utf-8")

        print(f"[storage-smoke] backend=seaweedfs key={key}")
        await storage.put_file(source, key, content_type="text/plain")
        if not await storage.exists(key):
            raise StorageError("Uploaded storage object does not exist")
        await storage.materialize(key, destination)
        if destination.read_text(encoding="utf-8") != source.read_text(encoding="utf-8"):
            raise StorageError("Materialized storage object does not match source")
        print("  upload/materialize: ok")
        origin = "http://localhost:5173"
        parsed = urlsplit(settings.storage_internal_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise StorageError(
                f"Invalid storage internal URL for browser delivery smoke: "
                f"{settings.storage_internal_url}",
            )

        connection_type = (
            http.client.HTTPSConnection
            if parsed.scheme == "https"
            else http.client.HTTPConnection
        )
        connection = connection_type(
            parsed.hostname,
            parsed.port,
            timeout=10,
        )
        try:
            request_path = (
                f"{parsed.path.rstrip('/')}/"
                f"{quote(key, safe='/')}"
            )
            connection.request(
                "GET",
                request_path,
                headers={
                    "Origin": origin,
                    "Range": "bytes=0-0",
                },
            )
            response = connection.getresponse()
            body = response.read()
            if response.status != 206:
                raise StorageError(
                    "Browser media smoke expected HTTP 206 for byte range, "
                    f"got {response.status}",
                )
            allow_origin = response.getheader("Access-Control-Allow-Origin")
            if allow_origin not in {origin, "*"}:
                raise StorageError(
                    "Browser media smoke missing expected CORS origin: "
                    f"{allow_origin!r}",
                )
            if not body:
                raise StorageError("Browser media smoke returned an empty byte range")
        finally:
            connection.close()

        print("  browser CORS/range delivery: ok")

        await storage.delete(key)
        if await storage.exists(key):
            raise StorageError("Deleted storage object still exists")
        print("  delete: ok")

    print("[storage-smoke] PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except StorageError as exc:
        print(f"[storage-smoke] FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc