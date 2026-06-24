import shutil
from contextlib import suppress
from pathlib import Path
from urllib.parse import quote

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings
from app.services.archive_service import ArchiveService
from app.services.archive_validation_service import ArchiveValidationService
from app.services.metadata_service import MetadataService
from app.services.project_service import ProjectService


class UploadService:
    def __init__(
        self,
        archive_service: ArchiveService,
        metadata_service: MetadataService,
        archive_validation_service: ArchiveValidationService,
        project_service: ProjectService,
    ):
        self.archive_service = archive_service
        self.metadata_service = metadata_service
        self.archive_validation_service = archive_validation_service
        self.project_service = project_service

    async def process_archive_upload(
        self,
        archive: UploadFile,
    ):
        archive_path = await self.archive_service.save_archive(archive)
        extracted_dir: Path | None = None

        try:
            extracted_dir = self.archive_service.extract_archive(archive_path)

            metadata = self.metadata_service.read_metadata(extracted_dir)
            self.metadata_service.validate_metadata(metadata)

            self.archive_validation_service.validate_dataset_structure(
                extracted_dir=extracted_dir,
                metadata=metadata,
            )

            tasks = self._build_label_studio_tasks(
                extracted_dir=extracted_dir,
                metadata=metadata,
            )

            project = await self.project_service.create_project_from_metadata_with_tasks(
                metadata=metadata,
                tasks=tasks,
            )
        except Exception:
            self._cleanup_failed_upload(archive_path, extracted_dir)
            raise

        return {
            "status": "success",
            "project_id": project["project_id"],
            "project_name": project["project_name"],
            "saved_archive_path": str(archive_path),
            "extracted_dir": str(extracted_dir),
            "classes": list(metadata["classes"].keys()),
            "imported_tasks_count": project["imported_tasks_count"],
        }

    def _build_label_studio_tasks(
        self,
        extracted_dir: Path,
        metadata: dict,
    ) -> list[dict]:
        dataset_root = self._find_dataset_root(extracted_dir)
        document_root = Path(settings.LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT)
        resolved_document_root = document_root.resolve(strict=False)

        tasks = []
        for class_name, class_info in metadata["classes"].items():
            images_dir = dataset_root / Path(class_info["directory"]) / "images"
            images = sorted(
                path
                for path in images_dir.iterdir()
                if path.is_file()
                and path.suffix.lower()
                in self.archive_validation_service.ALLOWED_IMAGE_EXTENSIONS
            )

            for image_path in images:
                relative_image_path = self._relative_to_document_root(
                    path=image_path,
                    document_root=resolved_document_root,
                )
                tasks.append(
                    {
                        "data": {
                            "image": self._local_file_url(relative_image_path),
                        },
                        "meta": {
                            "class": class_name,
                            "article": class_info["article"],
                            "source_path": relative_image_path.as_posix(),
                        },
                    }
                )

        return tasks

    def _find_dataset_root(self, extracted_dir: Path) -> Path:
        direct_metadata = extracted_dir / "metadata.json"

        if direct_metadata.exists():
            return extracted_dir

        candidates = list(extracted_dir.glob("*/metadata.json"))

        if len(candidates) == 1:
            return candidates[0].parent

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot determine dataset root directory",
        )

    def _relative_to_document_root(
        self,
        path: Path,
        document_root: Path,
    ) -> Path:
        resolved_path = path.resolve(strict=False)

        try:
            return resolved_path.relative_to(document_root)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "Extracted image is outside "
                    "LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT"
                ),
            ) from exc

    def _local_file_url(self, relative_path: Path) -> str:
        return f"/data/local-files/?d={quote(relative_path.as_posix(), safe='/')}"

    def _cleanup_failed_upload(
        self,
        archive_path: Path,
        extracted_dir: Path | None,
    ) -> None:
        with suppress(OSError):
            archive_path.unlink(missing_ok=True)

        if extracted_dir is not None:
            with suppress(OSError):
                shutil.rmtree(extracted_dir)
