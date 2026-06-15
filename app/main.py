from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/api/v1/docs",
        openapi_url="/api/v1/openapi.json",
    )

    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()