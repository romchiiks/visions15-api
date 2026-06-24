from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.model_storage_service import ModelStorageService


class FakeObjectResponse:
    def __init__(self, data: bytes):
        self.data = data

    def stream(self, chunk_size: int):
        for offset in range(0, len(self.data), chunk_size):
            yield self.data[offset : offset + chunk_size]

    def close(self):
        pass

    def release_conn(self):
        pass


class FakeMinioClient:
    def __init__(self):
        self.objects = {}
        self.buckets = set()

    def bucket_exists(self, bucket_name):
        return bucket_name in self.buckets

    def make_bucket(self, bucket_name):
        self.buckets.add(bucket_name)

    def get_object(self, bucket_name, object_name):
        return FakeObjectResponse(self.objects[(bucket_name, object_name)])

    def put_object(self, bucket_name, object_name, data, length, content_type):
        self.objects[(bucket_name, object_name)] = data.read(length)


def test_generate_manifest_uses_expected_defaults():
    service = ModelStorageService.__new__(ModelStorageService)

    manifest = service.generate_manifest(
        sha256="abc123",
        classes=["bolt", "nut"],
        img_size=1024,
        notes="fine-tuned",
        created_at=datetime(2026, 6, 24, 12, 0, tzinfo=timezone.utc),
    )

    assert manifest == {
        "version": "2026.06.24-001",
        "model_file": "model.pt",
        "sha256": "abc123",
        "classes": ["bolt", "nut"],
        "created_at": "2026-06-24T12:00:00Z",
        "img_size": 1024,
        "model_type": "yolo",
        "notes": "fine-tuned",
    }


def test_build_latest_bundle_contains_model_and_manifest(tmp_path):
    service = ModelStorageService.__new__(ModelStorageService)
    service.client = FakeMinioClient()
    service.bucket_name = "visions15-models"
    service.prefix = "model"
    service._bucket_ready = False
    service.client.buckets.add(service.bucket_name)
    service.client.objects[
        (service.bucket_name, "model/latest/model.pt")
    ] = b"model-bytes"
    service.client.objects[
        (service.bucket_name, "model/latest/manifest.json")
    ] = b'{"version":"2026.06.24-001","model_file":"model.pt"}'

    bundle = service.build_latest_bundle()
    archive_path = Path(tmp_path / "bundle.zip")
    archive_path.write_bytes(bundle.file.read())
    bundle.file.close()

    with ZipFile(archive_path) as archive:
        assert sorted(archive.namelist()) == ["manifest.json", "model.pt"]
        assert archive.read("model.pt") == b"model-bytes"
        assert b"2026.06.24-001" in archive.read("manifest.json")


def test_roll_back_copies_release_to_latest():
    service = ModelStorageService.__new__(ModelStorageService)
    service.client = FakeMinioClient()
    service.bucket_name = "visions15-models"
    service.prefix = "model"
    service._bucket_ready = False
    service.client.buckets.add(service.bucket_name)
    service.client.objects[
        (service.bucket_name, "model/releases/23-06-2026/model.pt")
    ] = b"release-model"
    service.client.objects[
        (service.bucket_name, "model/releases/23-06-2026/manifest.json")
    ] = b'{"version":"2026.06.23-001","model_file":"model.pt"}'

    manifest = service.roll_back("23-06-2026")

    assert manifest["version"] == "2026.06.23-001"
    assert (
        service.client.objects[(service.bucket_name, "model/latest/model.pt")]
        == b"release-model"
    )
    assert (
        b"2026.06.23-001"
        in service.client.objects[
            (service.bucket_name, "model/latest/manifest.json")
        ]
    )


def test_model_endpoints_require_api_key():
    client = TestClient(create_app())

    assert client.get("/api/v1/model/manifest").status_code == 401
    assert client.get("/api/v1/model/latest").status_code == 401
