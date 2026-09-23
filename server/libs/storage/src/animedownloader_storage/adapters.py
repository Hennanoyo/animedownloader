from __future__ import annotations

import asyncio
import http.client
import mimetypes
import shutil
from pathlib import Path
from urllib.parse import quote, urlsplit

from .exceptions import StorageError, StorageObjectNotFoundError


def _validate_object_key(object_key: str) -> str:
    key = object_key.strip("/")
    if not key:
        raise StorageError("Storage object key must not be empty")
    parts = Path(key).parts
    if Path(key).is_absolute() or ".." in parts:
        raise StorageError(f"Invalid storage object key: {object_key}")
    return key


def _public_url(endpoint: str, object_key: str) -> str:
    key = _validate_object_key(object_key)
    return f"{endpoint.rstrip('/')}/{quote(key, safe='/')}"


class LocalStorage:
    def __init__(self, root: Path, public_endpoint: str) -> None:
        self._root = root.resolve()
        self._public_endpoint = public_endpoint

    def _resolve_key(self, object_key: str) -> Path:
        key = _validate_object_key(object_key)
        path = (self._root / key).resolve()
        try:
            path.relative_to(self._root)
        except ValueError as exc:
            raise StorageError(f"Storage object key escapes storage root: {object_key}") from exc
        return path

    def _resolve_source(self, object_key: str) -> Path:
        legacy = Path(object_key)
        if legacy.is_absolute():
            path = legacy.resolve()
            try:
                path.relative_to(self._root)
            except ValueError as exc:
                raise StorageError(
                    f"Legacy storage path escapes storage root: {object_key}",
                ) from exc
            return path
        return self._resolve_key(object_key)

    async def put_file(
        self,
        source_path: Path,
        object_key: str,
        *,
        content_type: str | None = None,
    ) -> None:
        del content_type
        source = source_path.resolve()
        if not source.is_file():
            raise StorageError(f"Source file does not exist: {source_path}")
        destination = self._resolve_key(object_key)
        await asyncio.to_thread(self._copy_file, source, destination)

    async def materialize(self, object_key: str, destination: Path) -> Path:
        source = self._resolve_source(object_key)
        if not source.is_file():
            raise StorageObjectNotFoundError(object_key)
        await asyncio.to_thread(self._copy_file, source, destination)
        return destination

    async def exists(self, object_key: str) -> bool:
        try:
            source = self._resolve_source(object_key)
        except StorageError:
            return False
        return await asyncio.to_thread(source.is_file)

    async def delete(self, object_key: str) -> None:
        path = self._resolve_key(object_key)
        await asyncio.to_thread(self._unlink, path)

    def public_url(self, object_key: str) -> str:
        return _public_url(self._public_endpoint, object_key)

    @staticmethod
    def _copy_file(source: Path, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source == destination:
            return
        shutil.copyfile(source, destination)

    @staticmethod
    def _unlink(path: Path) -> None:
        try:
            path.unlink()
        except FileNotFoundError:
            return


class SeaweedFSStorage:
    def __init__(
        self,
        endpoint: str,
        public_endpoint: str,
        *,
        timeout_seconds: float = 60.0,
    ) -> None:
        parsed = urlsplit(endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise StorageError(f"Invalid SeaweedFS endpoint: {endpoint}")
        self._scheme = parsed.scheme
        self._host = parsed.hostname or ""
        self._port = parsed.port
        self._base_path = parsed.path.rstrip("/")
        self._public_endpoint = public_endpoint
        self._timeout_seconds = timeout_seconds

    def _path(self, object_key: str) -> str:
        key = _validate_object_key(object_key)
        return f"{self._base_path}/{quote(key, safe='/')}"

    def _connection(self) -> http.client.HTTPConnection | http.client.HTTPSConnection:
        connection_type = (
            http.client.HTTPSConnection
            if self._scheme == "https"
            else http.client.HTTPConnection
        )
        return connection_type(
            self._host,
            self._port,
            timeout=self._timeout_seconds,
        )

    async def put_file(
        self,
        source_path: Path,
        object_key: str,
        *,
        content_type: str | None = None,
    ) -> None:
        await asyncio.to_thread(
            self._put_file_sync,
            source_path,
            object_key,
            content_type,
        )

    def _put_file_sync(
        self,
        source_path: Path,
        object_key: str,
        content_type: str | None,
    ) -> None:
        source = source_path.resolve()
        if not source.is_file():
            raise StorageError(f"Source file does not exist: {source_path}")

        detected_type = (
            content_type
            or mimetypes.guess_type(source.name)[0]
            or "application/octet-stream"
        )
        connection = self._connection()
        try:
            connection.request(
                "POST",
                self._path(object_key),
                headers={
                    "Content-Type": detected_type,
                    "Content-Length": str(source.stat().st_size),
                },
            )
            request = connection.sock
            if request is None:
                raise StorageError("SeaweedFS connection is not established")
            with source.open("rb") as stream:
                while chunk := stream.read(1024 * 1024):
                    request.sendall(chunk)
            response = connection.getresponse()
            body = response.read()
            if response.status >= 400:
                message = body.decode("utf-8", errors="replace").strip()
                raise StorageError(
                    f"SeaweedFS upload failed with HTTP {response.status}: {message}",
                )
        except OSError as exc:
            raise StorageError(f"SeaweedFS upload failed: {exc}") from exc
        finally:
            connection.close()

    async def materialize(self, object_key: str, destination: Path) -> Path:
        await asyncio.to_thread(self._materialize_sync, object_key, destination)
        return destination

    def _materialize_sync(self, object_key: str, destination: Path) -> None:
        connection = self._connection()
        try:
            connection.request("GET", self._path(object_key))
            response = connection.getresponse()
            if response.status == 404:
                response.read()
                raise StorageObjectNotFoundError(object_key)
            if response.status >= 400:
                body = response.read().decode("utf-8", errors="replace").strip()
                raise StorageError(
                    f"SeaweedFS download failed with HTTP {response.status}: {body}",
                )
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("wb") as stream:
                shutil.copyfileobj(response, stream, length=1024 * 1024)
        except (OSError, http.client.HTTPException) as exc:
            raise StorageError(f"SeaweedFS download failed: {exc}") from exc
        finally:
            connection.close()

    async def exists(self, object_key: str) -> bool:
        return await asyncio.to_thread(self._exists_sync, object_key)

    def _exists_sync(self, object_key: str) -> bool:
        connection = self._connection()
        try:
            connection.request("GET", self._path(object_key), headers={"Range": "bytes=0-0"})
            response = connection.getresponse()
            response.read(1)
            if response.status == 404:
                return False
            if response.status >= 400:
                body = response.read().decode("utf-8", errors="replace").strip()
                raise StorageError(
                    f"SeaweedFS existence check failed with HTTP {response.status}: {body}",
                )
            return True
        except (OSError, http.client.HTTPException) as exc:
            raise StorageError(f"SeaweedFS existence check failed: {exc}") from exc
        finally:
            connection.close()

    async def delete(self, object_key: str) -> None:
        await asyncio.to_thread(self._delete_sync, object_key)

    def _delete_sync(self, object_key: str) -> None:
        connection = self._connection()
        try:
            connection.request("DELETE", self._path(object_key))
            response = connection.getresponse()
            body = response.read()
            if response.status in {404, 200, 204}:
                return
            message = body.decode("utf-8", errors="replace").strip()
            raise StorageError(
                f"SeaweedFS delete failed with HTTP {response.status}: {message}",
            )
        except (OSError, http.client.HTTPException) as exc:
            raise StorageError(f"SeaweedFS delete failed: {exc}") from exc
        finally:
            connection.close()

    def public_url(self, object_key: str) -> str:
        return _public_url(self._public_endpoint, object_key)
