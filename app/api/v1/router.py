from fastapi import APIRouter

from app.api.v1.endpoints import health, model, projects, uploads

api_router = APIRouter()

api_router.include_router(
    health.router,
    prefix="/health",
    tags=["health"],
)

api_router.include_router(
    uploads.router,
    prefix="/uploads",
    tags=["uploads"],
)

api_router.include_router(
    projects.router,
    prefix="/projects",
    tags=["projects"],
)

api_router.include_router(
    model.router,
    prefix="/model",
    tags=["model"],
)
