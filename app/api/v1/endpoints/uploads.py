from fastapi import APIRouter, Depends, File, UploadFile

from app.api.deps import get_upload_service
from app.core.security import require_api_key
from app.schemas.upload import UploadArchiveResponse
from app.services.upload_service import UploadService

router = APIRouter()


@router.post(
    "/archive",
    response_model=UploadArchiveResponse,
    dependencies=[Depends(require_api_key)],
)
async def upload_archive(
    archive: UploadFile = File(...),
    upload_service: UploadService = Depends(get_upload_service),
):
    return await upload_service.process_archive_upload(
        archive=archive,
    )