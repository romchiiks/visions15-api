import json

import pytest
from fastapi import HTTPException

from app.services.metadata_service import MetadataService


def _valid_metadata():
    return {
        "schema_version": "1.0",
        "dataset_update": {"name": " Demo dataset "},
        "classes": {
            " cat ": {
                "article": "cat article",
                "directory": "cat",
                "images_count": 2,
            }
        },
    }


def test_read_metadata_finds_file_in_single_top_level_directory(tmp_path):
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir()
    metadata = _valid_metadata()
    (dataset_dir / "metadata.json").write_text(
        json.dumps(metadata),
        encoding="utf-8",
    )

    assert MetadataService().read_metadata(tmp_path) == metadata


def test_read_metadata_rejects_malformed_json(tmp_path):
    (tmp_path / "metadata.json").write_text("{broken", encoding="utf-8")

    with pytest.raises(HTTPException) as exc_info:
        MetadataService().read_metadata(tmp_path)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid metadata.json: malformed JSON"


def test_validate_metadata_normalizes_project_and_class_names():
    metadata = _valid_metadata()

    MetadataService().validate_metadata(metadata)

    assert metadata["dataset_update"]["name"] == "Demo dataset"
    assert list(metadata["classes"]) == ["cat"]


@pytest.mark.parametrize(
    ("metadata", "detail"),
    [
        ({}, "Unsupported or missing metadata schema_version"),
        (
            {"schema_version": "1.0"},
            "Missing dataset_update block in metadata.json",
        ),
        (
            {"schema_version": "1.0", "dataset_update": {"name": "Demo"}},
            "Missing classes block in metadata.json",
        ),
        (
            {
                "schema_version": "1.0",
                "dataset_update": {"name": "Demo"},
                "classes": {},
            },
            "metadata.classes must be a non-empty object",
        ),
    ],
)
def test_validate_metadata_rejects_invalid_metadata(metadata, detail):
    with pytest.raises(HTTPException) as exc_info:
        MetadataService().validate_metadata(metadata)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == detail


def test_validate_metadata_rejects_bool_images_count():
    metadata = _valid_metadata()
    metadata["classes"][" cat "]["images_count"] = True

    with pytest.raises(HTTPException) as exc_info:
        MetadataService().validate_metadata(metadata)

    assert exc_info.value.status_code == 400
    assert "images_count for class cat" in exc_info.value.detail
