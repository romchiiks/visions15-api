import hashlib
import json
import tempfile
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status


MODEL_FILE_NAME = "model.pt"
MANIFEST_FILE_NAME = "manifest.json"


@dataclass
class ModelBundle:
    file: tempfile.SpooledTemporaryFile
    manifest: dict[str, Any]


class ModelStorageService:
    def __init__(
        self,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket_name: str,
        prefix: str = "model",
        secure: bool = False,
    ):
        from minio import Minio

        self.client = Minio(
            endpoint_url,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )
        self.bucket_name = bucket_name
        self.prefix = prefix.strip("/")
        self._bucket_ready = False

    def latest_model_object_name(self) -> str:
        return self._object_name("latest", MODEL_FILE_NAME)

    def latest_manifest_object_name(self) -> str:
        return self._object_name("latest", MANIFEST_FILE_NAME)

    def release_model_object_name(self, release: str) -> str:
        return self._object_name("releases", release, MODEL_FILE_NAME)

    def release_manifest_object_name(self, release: str) -> str:
        return self._object_name("releases", release, MANIFEST_FILE_NAME)

    def get_latest_manifest(self) -> dict[str, Any]:
        return self.get_manifest(self.latest_manifest_object_name())

    def get_manifest(self, object_name: str) -> dict[str, Any]:
        data = self.get_object_bytes(object_name)

        try:
            manifest = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Model manifest is invalid",
            ) from exc

        if not isinstance(manifest, dict):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Model manifest must be a JSON object",
            )

        return manifest

    def build_latest_bundle(self) -> ModelBundle:
        manifest = self.get_latest_manifest()
        bundle = tempfile.SpooledTemporaryFile(max_size=64 * 1024 * 1024)

        try:
            with zipfile.ZipFile(
                bundle,
                mode="w",
                compression=zipfile.ZIP_DEFLATED,
            ) as archive:
                archive.writestr(
                    MANIFEST_FILE_NAME,
                    json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"),
                )

                with archive.open(MODEL_FILE_NAME, mode="w") as model_entry:
                    self.write_object_to_file(
                        self.latest_model_object_name(),
                        model_entry,
                    )
        except Exception:
            bundle.close()
            raise

        bundle.seek(0)
        return ModelBundle(file=bundle, manifest=manifest)

    def upload_new_model(
        self,
        source_path: Path,
        release: str,
        manifest: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._ensure_bucket()
        source_path = source_path.resolve()

        if not source_path.is_file():
            raise ValueError(f"Model source file does not exist: {source_path}")

        sha256 = self.sha256_file(source_path)
        if manifest is None:
            manifest = self.generate_manifest(sha256=sha256)
        else:
            manifest = {**manifest, "sha256": sha256, "model_file": MODEL_FILE_NAME}

        self._upload_file(source_path, self.latest_model_object_name())
        self._upload_manifest(manifest, self.latest_manifest_object_name())
        self._upload_file(source_path, self.release_model_object_name(release))
        self._upload_manifest(manifest, self.release_manifest_object_name(release))

        return manifest

    def roll_back(
        self,
        release: str,
        manifest: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._ensure_bucket()

        release_model = self.release_model_object_name(release)
        sha256 = self.sha256_object(release_model)

        if manifest is None:
            try:
                manifest = self.get_manifest(self.release_manifest_object_name(release))
            except HTTPException as exc:
                if exc.status_code != status.HTTP_404_NOT_FOUND:
                    raise
                manifest = self.generate_manifest(sha256=sha256)
        else:
            manifest = {**manifest, "sha256": sha256, "model_file": MODEL_FILE_NAME}

        self.copy_object(release_model, self.latest_model_object_name())
        self._upload_manifest(manifest, self.latest_manifest_object_name())

        return manifest

    def generate_manifest(
        self,
        *,
        sha256: str,
        version: str | None = None,
        classes: list[str] | None = None,
        img_size: int | None = None,
        model_type: str | None = "yolo",
        notes: str = "",
        created_at: datetime | None = None,
        base_manifest: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = created_at or datetime.now(timezone.utc)
        base = dict(base_manifest or {})

        manifest: dict[str, Any] = {
            "version": version or base.get("version") or now.strftime("%Y.%m.%d-001"),
            "model_file": MODEL_FILE_NAME,
            "sha256": sha256,
            "classes": classes if classes is not None else base.get("classes", []),
            "created_at": now.isoformat().replace("+00:00", "Z"),
            "img_size": img_size if img_size is not None else base.get("img_size"),
            "model_type": model_type or base.get("model_type", "yolo"),
            "notes": notes if notes else base.get("notes", ""),
        }

        return manifest

    def get_object_bytes(self, object_name: str) -> bytes:
        data = bytearray()
        response = self._get_object(object_name)
        try:
            for chunk in response.stream(1024 * 1024):
                data.extend(chunk)
        finally:
            response.close()
            response.release_conn()

        return bytes(data)

    def write_object_to_file(self, object_name: str, target) -> None:
        response = self._get_object(object_name)
        try:
            for chunk in response.stream(1024 * 1024):
                target.write(chunk)
        finally:
            response.close()
            response.release_conn()

    def sha256_object(self, object_name: str) -> str:
        digest = hashlib.sha256()
        response = self._get_object(object_name)
        try:
            for chunk in response.stream(1024 * 1024):
                digest.update(chunk)
        finally:
            response.close()
            response.release_conn()

        return digest.hexdigest()

    def copy_object(self, source_object_name: str, target_object_name: str) -> None:
        self._ensure_bucket()
        temp_file = tempfile.SpooledTemporaryFile(max_size=64 * 1024 * 1024)
        length = 0

        try:
            response = self._get_object(source_object_name)
            try:
                for chunk in response.stream(1024 * 1024):
                    temp_file.write(chunk)
                    length += len(chunk)
            finally:
                response.close()
                response.release_conn()

            temp_file.seek(0)

            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=target_object_name,
                data=temp_file,
                length=length,
                content_type="application/octet-stream",
            )
        except Exception as exc:
            self._raise_storage_error(exc, "Model object copy failed")
        finally:
            temp_file.close()

    def _upload_file(self, source_path: Path, object_name: str) -> None:
        try:
            self.client.fput_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                file_path=str(source_path),
                content_type="application/octet-stream",
            )
        except Exception as exc:
            self._raise_storage_error(exc, "Model upload failed")

    def _upload_manifest(self, manifest: dict[str, Any], object_name: str) -> None:
        data = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")

        try:
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=_BytesIterator(data),
                length=len(data),
                content_type="application/json",
            )
        except Exception as exc:
            self._raise_storage_error(exc, "Model manifest upload failed")

    def _get_object(self, object_name: str):
        self._ensure_bucket()

        try:
            return self.client.get_object(self.bucket_name, object_name)
        except Exception as exc:
            self._raise_storage_error(exc, "Model object read failed")

    def _ensure_bucket(self) -> None:
        if self._bucket_ready:
            return

        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
        except Exception as exc:
            self._raise_storage_error(exc, "Model bucket initialization failed")

        self._bucket_ready = True

    def _object_name(self, *parts: str) -> str:
        clean_parts = [part.strip("/") for part in parts if part.strip("/")]
        if self.prefix:
            clean_parts.insert(0, self.prefix)

        return "/".join(clean_parts)

    def _raise_storage_error(self, exc: Exception, detail: str) -> None:
        if _is_missing_object_error(exc):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Model object not found",
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail,
        ) from exc

    @staticmethod
    def sha256_file(path: Path) -> str:
        digest = hashlib.sha256()

        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)

        return digest.hexdigest()


class _BytesIterator:
    def __init__(self, data: bytes):
        self._data = data
        self._offset = 0

    def read(self, size: int = -1) -> bytes:
        if self._offset >= len(self._data):
            return b""

        if size is None or size < 0:
            size = len(self._data) - self._offset

        chunk = self._data[self._offset : self._offset + size]
        self._offset += len(chunk)
        return chunk


def iter_file_chunks(file, chunk_size: int = 1024 * 1024) -> Iterator[bytes]:
    try:
        while chunk := file.read(chunk_size):
            yield chunk
    finally:
        file.close()


def _is_missing_object_error(exc: Exception) -> bool:
    code = getattr(exc, "code", None)
    return code in {"NoSuchKey", "NoSuchObject", "NoSuchBucket"}
