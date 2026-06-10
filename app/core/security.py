from fastapi import Header, HTTPException, status

from app.core.config import settings
from app.services.api_key_service import ApiKeyService


async def require_api_key(
    x_api_key: str | None = Header(default=None),
) -> None:
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )

    api_key_service = ApiKeyService(settings.API_KEYS_FILE)

    if not api_key_service.verify_api_key(x_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )