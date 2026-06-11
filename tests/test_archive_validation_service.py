import pytest
from fastapi import HTTPException

from app.services.archive_validation_service import ArchiveValidationService


def _metadata(images_count=2, directory="cat"):
    return {
        "classes": {
            "cat": {
                "article": "cat article",
                "directory": directory,
                "images_count": images_count,
            }
        }
    }


def test_validate_dataset_structure_accepts_expected_images(tmp_path):
    dataset_root = tmp_path / "dataset"
    images_dir = dataset_root / "cat" / "images"
    images_dir.mkdir(parents=True)
    (dataset_root / "metadata.json").write_text("{}", encoding="utf-8")
    (images_dir / "first.JPG").write_bytes(b"image")
    (images_dir / "second.png").write_bytes(b"image")
    (images_dir / "ignored.txt").write_text("not image", encoding="utf-8")

    ArchiveValidationService().validate_dataset_structure(
        extracted_dir=dataset_root,
        metadata=_metadata(),
    )


def test_validate_dataset_structure_detects_count_mismatch(tmp_path):
    dataset_root = tmp_path / "dataset"
    images_dir = dataset_root / "cat" / "images"
    images_dir.mkdir(parents=True)
    (dataset_root / "metadata.json").write_text("{}", encoding="utf-8")
    (images_dir / "first.jpg").write_bytes(b"image")

    with pytest.raises(HTTPException) as exc_info:
        ArchiveValidationService().validate_dataset_structure(
            extracted_dir=dataset_root,
            metadata=_metadata(images_count=2),
        )

    assert exc_info.value.status_code == 400
    assert "Images count mismatch" in exc_info.value.detail


@pytest.mark.parametrize("directory", ["../cat", "cat/../dog", "/cat", "cat//dog", "C:\\cat"])
def test_validate_dataset_structure_rejects_unsafe_class_directory(tmp_path, directory):
    dataset_root = tmp_path / "dataset"
    dataset_root.mkdir()
    (dataset_root / "metadata.json").write_text("{}", encoding="utf-8")

    with pytest.raises(HTTPException) as exc_info:
        ArchiveValidationService().validate_dataset_structure(
            extracted_dir=dataset_root,
            metadata=_metadata(images_count=0, directory=directory),
        )

    assert exc_info.value.status_code == 400
