import json
import mimetypes
from pathlib import Path
from urllib.parse import quote

from fastapi import HTTPException, status


class ObjectStorageService:
    def __init__(
        self,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket_name: str,
        public_base_url: str,
        secure: bool = False,
        bucket_public_read: bool = True,
    ):
        from minio import Minio

        self.client = Minio(
            endpoint_url,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )
        self.bucket_name = bucket_name
        self.public_base_url = public_base_url.rstrip("/")
        self.bucket_public_read = bucket_public_read
        self._bucket_ready = False

    def upload_file(self, source_path: Path, object_name: str) -> str:
        self._ensure_bucket()

        content_type = (
            mimetypes.guess_type(source_path.name)[0]
            or "application/octet-stream"
        )

        try:
            self.client.fput_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                file_path=str(source_path),
                content_type=content_type,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Object storage upload failed",
            ) from exc

        return self.public_url(object_name)

    def public_url(self, object_name: str) -> str:
        return f"{self.public_base_url}/{quote(object_name, safe='/')}"

    def _ensure_bucket(self) -> None:
        if self._bucket_ready:
            return

        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)

            if self.bucket_public_read:
                self.client.set_bucket_policy(
                    self.bucket_name,
                    json.dumps(self._public_read_policy()),
                )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Object storage bucket initialization failed",
            ) from exc

        self._bucket_ready = True

    def _public_read_policy(self) -> dict:
        return {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{self.bucket_name}/*"],
                }
            ],
        }
