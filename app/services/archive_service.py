import shutil
import tarfile
import zipfile
from contextlib import suppress
from pathlib import Path, PurePosixPath, PureWindowsPath
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings
from app.utils.filenames import sanitize_filename


class ArchiveService:
    _COPY_CHUNK_SIZE = 1024 * 1024

    async def save_archive(self, archive: UploadFile) -> Path:
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)

        # max_archive_size_bytes = settings.MAX_ARCHIVE_SIZE_MB * 1024 * 1024
        # upload_size = getattr(archive, "size", None)
        # if upload_size is not None and upload_size > max_archive_size_bytes:
        #     self._raise_archive_too_large()

        archive_id = uuid4().hex
        archive_name = sanitize_filename(archive.filename or "dataset.zip") or "dataset.zip"
        archive_path = upload_dir / f"{archive_id}_{archive_name}"

        written_bytes = 0
        try:
            with archive_path.open("wb") as buffer:
                while chunk := await archive.read(self._COPY_CHUNK_SIZE):
                    written_bytes += len(chunk)
                    # if written_bytes > max_archive_size_bytes:
                        # self._raise_archive_too_large()
                    buffer.write(chunk)
        except HTTPException:
            archive_path.unlink(missing_ok=True)
            raise

        return archive_path

    # def _raise_archive_too_large(self) -> None:
    #     raise HTTPException(
    #         status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
    #         detail=f"Archive size exceeds {settings.MAX_ARCHIVE_SIZE_MB} MB limit.",
    #     )

    def _raise_unsafe_archive_entry(self, entry_name: str) -> None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Archive contains unsafe entry: {entry_name}",
        )

    def extract_archive(self, archive_path: Path) -> Path:
        extracted_root = Path(settings.EXTRACTED_DIR)
        extracted_root.mkdir(parents=True, exist_ok=True)

        target_dir = extracted_root / archive_path.stem
        target_dir_existed = target_dir.exists()
        target_dir.mkdir(parents=True, exist_ok=True)

        try:
            if zipfile.is_zipfile(archive_path):
                self._extract_zip_safely(archive_path, target_dir)
                return target_dir

            if tarfile.is_tarfile(archive_path):
                self._extract_tar_safely(archive_path, target_dir)
                return target_dir

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported archive format. Use .zip, .tar, .tar.gz",
            )
        except Exception:
            if not target_dir_existed:
                with suppress(OSError):
                    shutil.rmtree(target_dir)
            raise

    def _extract_zip_safely(self, archive_path: Path, target_dir: Path) -> None:
        with zipfile.ZipFile(archive_path, "r") as archive:
            for entry in archive.infolist():
                self._safe_archive_destination(entry.filename, target_dir)

            archive.extractall(target_dir)

    def _extract_tar_safely(self, archive_path: Path, target_dir: Path) -> None:
        with tarfile.open(archive_path, "r:*") as archive:
            for entry in archive.getmembers():
                if entry.issym() or entry.islnk() or not (entry.isfile() or entry.isdir()):
                    self._raise_unsafe_archive_entry(entry.name)

                self._safe_archive_destination(entry.name, target_dir)

            archive.extractall(target_dir, filter="data")

    def _safe_archive_destination(self, entry_name: str, target_dir: Path) -> Path:
        normalized_name = entry_name.replace("\\", "/")
        posix_path = PurePosixPath(normalized_name)
        windows_path = PureWindowsPath(normalized_name)

        if (
            not normalized_name
            or posix_path.is_absolute()
            or windows_path.is_absolute()
            or any(part in {"", ".", ".."} for part in posix_path.parts)
            or any(":" in part for part in posix_path.parts)
        ):
            self._raise_unsafe_archive_entry(entry_name)

        target_root = target_dir.resolve()
        destination = (target_root / Path(*posix_path.parts)).resolve()

        try:
            destination.relative_to(target_root)
        except ValueError:
            self._raise_unsafe_archive_entry(entry_name)

        return destination
