from fastapi import UploadFile

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
        extracted_dir = self.archive_service.extract_archive(archive_path)

        metadata = self.metadata_service.read_metadata(extracted_dir)
        self.metadata_service.validate_metadata(metadata)

        self.archive_validation_service.validate_dataset_structure(
            extracted_dir=extracted_dir,
            metadata=metadata,
        )

        project = await self.project_service.create_project_from_metadata(
            metadata=metadata,
        )

        return {
            "status": "success",
            "project_id": project["project_id"],
            "project_name": project["project_name"],
            "saved_archive_path": str(archive_path),
            "extracted_dir": str(extracted_dir),
            "classes": list(metadata["classes"].keys()),
        }