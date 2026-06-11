import io
import tarfile
import zipfile

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.services.archive_service import ArchiveService


def test_extract_zip_rejects_path_traversal(tmp_path, monkeypatch):
    archive_path = tmp_path / "dataset.zip"
    extract_dir = tmp_path / "extracted"
    monkeypatch.setattr(settings, "EXTRACTED_DIR", str(extract_dir))

    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../metadata.json", "{}")

    with pytest.raises(HTTPException) as exc_info:
        ArchiveService().extract_archive(archive_path)

    assert exc_info.value.status_code == 400
    assert "unsafe entry" in exc_info.value.detail
    assert not (extract_dir / archive_path.stem).exists()


def test_extract_tar_rejects_symlink_entries(tmp_path, monkeypatch):
    archive_path = tmp_path / "dataset.tar"
    extract_dir = tmp_path / "extracted"
    monkeypatch.setattr(settings, "EXTRACTED_DIR", str(extract_dir))

    with tarfile.open(archive_path, "w") as archive:
        metadata = b"{}"
        metadata_info = tarfile.TarInfo("metadata.json")
        metadata_info.size = len(metadata)
        archive.addfile(metadata_info, io.BytesIO(metadata))

        link_info = tarfile.TarInfo("class/images/link.jpg")
        link_info.type = tarfile.SYMTYPE
        link_info.linkname = "/etc/passwd"
        archive.addfile(link_info)

    with pytest.raises(HTTPException) as exc_info:
        ArchiveService().extract_archive(archive_path)

    assert exc_info.value.status_code == 400
    assert "unsafe entry" in exc_info.value.detail
    assert not (extract_dir / archive_path.stem).exists()


def test_extract_archive_rejects_unknown_file_format(tmp_path, monkeypatch):
    archive_path = tmp_path / "dataset.txt"
    archive_path.write_text("not an archive", encoding="utf-8")
    extract_dir = tmp_path / "extracted"
    monkeypatch.setattr(settings, "EXTRACTED_DIR", str(extract_dir))

    with pytest.raises(HTTPException) as exc_info:
        ArchiveService().extract_archive(archive_path)

    assert exc_info.value.status_code == 400
    assert "Unsupported archive format" in exc_info.value.detail
