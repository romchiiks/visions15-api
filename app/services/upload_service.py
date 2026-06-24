import shutil
from contextlib import suppress
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.services.archive_service import ArchiveService
from app.services.archive_validation_service import ArchiveValidationService
from app.services.metadata_service import MetadataService
from app.services.object_storage_service import ObjectStorageService
from app.services.project_service import ProjectService


class UploadService:
    def __init__(
        self,
        archive_service: ArchiveService,
        metadata_service: MetadataService,
        archive_validation_service: ArchiveValidationService,
        object_storage_service: ObjectStorageService,
        project_service: ProjectService,
    ):
        self.archive_service = archive_service
        self.metadata_service = metadata_service
        self.archive_validation_service = archive_validation_service
        self.object_storage_service = object_storage_service
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

            tasks_by_class = self._build_label_studio_tasks_by_class(
                extracted_dir=extracted_dir,
                metadata=metadata,
            )

            create_projects = (
                self.project_service.create_projects_from_metadata_with_tasks_by_class
            )
            projects = await create_projects(
                metadata=metadata,
                tasks_by_class=tasks_by_class,
            )
        except Exception:
            self._cleanup_failed_upload(archive_path, extracted_dir)
            raise

        return {
            "status": "success",
            "projects": projects,
            "saved_archive_path": str(archive_path),
            "extracted_dir": str(extracted_dir),
            "classes": list(metadata["classes"].keys()),
            "imported_tasks_count": sum(
                project["imported_tasks_count"] for project in projects
            ),
        }

    def _build_label_studio_tasks(
        self,
        extracted_dir: Path,
        metadata: dict,
    ) -> list[dict]:
        tasks_by_class = self._build_label_studio_tasks_by_class(
            extracted_dir=extracted_dir,
            metadata=metadata,
        )

        return [
            task
            for class_tasks in tasks_by_class.values()
            for task in class_tasks
        ]

    def _build_label_studio_tasks_by_class(
        self,
        extracted_dir: Path,
        metadata: dict,
    ) -> dict[str, list[dict]]:
        dataset_root = self._find_dataset_root(extracted_dir)

        tasks_by_class = {}
        for class_name, class_info in metadata["classes"].items():
            tasks_by_class[class_name] = []
            images_dir = dataset_root / Path(class_info["directory"]) / "images"
            images = sorted(
                path
                for path in images_dir.iterdir()
                if path.is_file()
                and path.suffix.lower()
                in self.archive_validation_service.ALLOWED_IMAGE_EXTENSIONS
            )

            for image_path in images:
                object_name = self._storage_object_name(
                    extracted_dir=extracted_dir,
                    dataset_root=dataset_root,
                    image_path=image_path,
                )
                image_url = self.object_storage_service.upload_file(
                    source_path=image_path,
                    object_name=object_name,
                )
                task = {
                    "data": {
                        "image": image_url,
                    },
                    "meta": {
                        "class": class_name,
                        "article": class_info["article"],
                        "source_path": object_name,
                    },
                }
                tasks_by_class[class_name].append(task)

        return tasks_by_class

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

    def _storage_object_name(
        self,
        extracted_dir: Path,
        dataset_root: Path,
        image_path: Path,
    ) -> str:
        relative_image_path = image_path.relative_to(dataset_root)

        if dataset_root == extracted_dir:
            dataset_relative_path = relative_image_path
        else:
            dataset_relative_path = Path(dataset_root.name) / relative_image_path

        return f"datasets/{extracted_dir.name}/{dataset_relative_path.as_posix()}"

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
