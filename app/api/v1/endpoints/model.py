from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse

from app.api.deps import get_model_storage_service
from app.core.security import require_api_key
from app.services.model_storage_service import (
    ModelStorageService,
    iter_file_chunks,
)

router = APIRouter()


@router.get(
    "/latest",
    dependencies=[Depends(require_api_key)],
)
@router.get(
    "/latest/",
    dependencies=[Depends(require_api_key)],
    include_in_schema=False,
)
def download_latest_model(
    model_storage_service: ModelStorageService = Depends(get_model_storage_service),
):
    bundle = model_storage_service.build_latest_bundle()
    version = str(bundle.manifest.get("version") or "latest")

    return StreamingResponse(
        iter_file_chunks(bundle.file),
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                f'attachment; filename="model-{version}.zip"'
            )
        },
    )


@router.get(
    "/manifest",
    dependencies=[Depends(require_api_key)],
)
@router.get(
    "/manifest/",
    dependencies=[Depends(require_api_key)],
    include_in_schema=False,
)
def get_latest_manifest(
    model_storage_service: ModelStorageService = Depends(get_model_storage_service),
):
    return JSONResponse(model_storage_service.get_latest_manifest())
