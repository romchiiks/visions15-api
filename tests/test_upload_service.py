from app.core.config import settings
from app.services.archive_validation_service import ArchiveValidationService
from app.services.upload_service import UploadService


def test_build_label_studio_tasks_uses_local_file_urls(tmp_path, monkeypatch):
    document_root = tmp_path / "files"
    extracted_dir = document_root / "extracted" / "archive"
    images_dir = extracted_dir / "cat" / "images"
    images_dir.mkdir(parents=True)
    (extracted_dir / "metadata.json").write_text("{}", encoding="utf-8")
    (images_dir / "first image.JPG").write_bytes(b"image")
    (images_dir / "ignored.txt").write_text("not image", encoding="utf-8")
    monkeypatch.setattr(
        settings,
        "LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT",
        str(document_root),
    )

    service = UploadService(
        archive_service=None,
        metadata_service=None,
        archive_validation_service=ArchiveValidationService(),
        project_service=None,
    )

    tasks = service._build_label_studio_tasks(
        extracted_dir=extracted_dir,
        metadata={
            "classes": {
                "cat": {
                    "article": "cat article",
                    "directory": "cat",
                    "images_count": 1,
                }
            }
        },
    )

    assert tasks == [
        {
            "data": {
                "image": (
                    "/data/local-files/?d="
                    "extracted/archive/cat/images/first%20image.JPG"
                ),
            },
            "meta": {
                "class": "cat",
                "article": "cat article",
                "source_path": "extracted/archive/cat/images/first image.JPG",
            },
        }
    ]
