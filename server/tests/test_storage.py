from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest
from animedownloader_storage import (
    LocalStorage,
    SeaweedFSStorage,
    StorageError,
    StorageObjectNotFoundError,
    create_storage,
)


@pytest.mark.anyio
async def test_local_storage_round_trip(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path / "objects", "http://localhost:8888")
    source = tmp_path / "source.bin"
    source.write_bytes(b"hello storage")

    await storage.put_file(source, "media/example.bin")
    assert await storage.exists("media/example.bin")

    destination = tmp_path / "materialized.bin"
    await storage.materialize("media/example.bin", destination)
    assert destination.read_bytes() == b"hello storage"
    assert storage.public_url("media/example.bin") == "http://localhost:8888/media/example.bin"

    await storage.delete("media/example.bin")
    assert not await storage.exists("media/example.bin")


@pytest.mark.anyio
async def test_local_storage_supports_legacy_absolute_paths(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path / "objects", "http://localhost:8888")
    legacy = tmp_path / "objects" / "legacy.bin"
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(b"legacy")

    destination = tmp_path / "copy.bin"
    await storage.materialize(str(legacy), destination)

    assert destination.read_bytes() == b"legacy"


@pytest.mark.anyio
async def test_storage_rejects_unsafe_keys(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path, "http://localhost:8888")
    source = tmp_path / "source.bin"
    source.write_bytes(b"content")

    with pytest.raises(StorageError):
        await storage.put_file(source, "../escape")

    with pytest.raises(StorageError):
        await storage.put_file(source, "/absolute")


@pytest.mark.anyio
async def test_seaweedfs_storage_round_trip(tmp_path: Path) -> None:
    values: dict[str, bytes] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            size = int(self.headers.get("Content-Length", "0"))
            values[self.path] = self.rfile.read(size)
            self.send_response(201)
            self.end_headers()

        def do_GET(self) -> None:
            payload = values.get(self.path)
            if payload is None:
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_DELETE(self) -> None:
            values.pop(self.path, None)
            self.send_response(204)
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            return None

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        endpoint = f"http://127.0.0.1:{server.server_port}"
        storage = SeaweedFSStorage(endpoint, "http://localhost:8888")
        source = tmp_path / "source.txt"
        source.write_text("hello seaweed", encoding="utf-8")

        await storage.put_file(source, "smoke/example.txt", content_type="text/plain")
        assert await storage.exists("smoke/example.txt")

        destination = tmp_path / "download.txt"
        await storage.materialize("smoke/example.txt", destination)
        assert destination.read_text(encoding="utf-8") == "hello seaweed"
        assert storage.public_url("smoke/example.txt") == "http://localhost:8888/smoke/example.txt"

        await storage.delete("smoke/example.txt")
        assert not await storage.exists("smoke/example.txt")

        with pytest.raises(StorageObjectNotFoundError):
            await storage.materialize("smoke/example.txt", tmp_path / "missing.txt")
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_create_storage_selects_backend(tmp_path: Path) -> None:
    local = create_storage(
        backend="local",
        local_root=tmp_path,
        internal_url="http://storage:8888",
        public_url="http://localhost:8888",
    )
    seaweedfs = create_storage(
        backend="seaweedfs",
        local_root=tmp_path,
        internal_url="http://storage:8888",
        public_url="http://localhost:8888",
    )

    assert isinstance(local, LocalStorage)
    assert isinstance(seaweedfs, SeaweedFSStorage)


@pytest.mark.anyio
async def test_seaweedfs_upload_failure_is_storage_error(tmp_path: Path) -> None:
    storage = SeaweedFSStorage(
        "http://127.0.0.1:1",
        "http://localhost:8888",
        timeout_seconds=0.1,
    )
    source = tmp_path / "source.txt"
    source.write_text("content", encoding="utf-8")

    with pytest.raises(StorageError):
        await storage.put_file(source, "failure.txt")
