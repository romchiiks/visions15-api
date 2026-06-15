from app.clients.label_studio_client import LabelStudioClient
from app.core.config import settings
from app.services.archive_service import ArchiveService
from app.services.archive_validation_service import ArchiveValidationService
from app.services.label_config_service import LabelConfigService
from app.services.metadata_service import MetadataService
from app.services.project_service import ProjectService
from app.services.upload_service import UploadService


def get_label_studio_client() -> LabelStudioClient:
    return LabelStudioClient(
        base_url=settings.LABEL_STUDIO_URL,
        api_key=settings.LABEL_STUDIO_API_KEY,
        auth_scheme=settings.LABEL_STUDIO_AUTH_SCHEME,
    )


def get_archive_service() -> ArchiveService:
    return ArchiveService()


def get_metadata_service() -> MetadataService:
    return MetadataService()


def get_archive_validation_service() -> ArchiveValidationService:
    return ArchiveValidationService()


def get_label_config_service() -> LabelConfigService:
    return LabelConfigService()


def get_project_service() -> ProjectService:
    return ProjectService(
        label_studio_client=get_label_studio_client(),
        label_config_service=get_label_config_service(),
    )


def get_upload_service() -> UploadService:
    return UploadService(
        archive_service=get_archive_service(),
        metadata_service=get_metadata_service(),
        archive_validation_service=get_archive_validation_service(),
        project_service=get_project_service(),
    )
