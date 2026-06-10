from fastapi import APIRouter, Depends

from app.api.deps import get_project_service
from app.core.security import require_api_key
from app.schemas.project import CreateProjectRequest, CreateProjectResponse
from app.services.project_service import ProjectService

router = APIRouter()


@router.post(
    "",
    response_model=CreateProjectResponse,
    dependencies=[Depends(require_api_key)],
)
async def create_project(
    data: CreateProjectRequest,
    project_service: ProjectService = Depends(get_project_service),
):
    return await project_service.create_project(
        project_name=data.project_name,
        classes=data.classes,
    )