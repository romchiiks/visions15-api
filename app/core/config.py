from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Visions15-API"
    APP_VERSION: str = "0.1.0"

    LABEL_STUDIO_URL: str
    LABEL_STUDIO_API_KEY: str
    LABEL_STUDIO_AUTH_SCHEME: Literal["Bearer", "Token"] = "Token"

    UPLOAD_DIR: str = "/label-studio/files/uploads"
    EXTRACTED_DIR: str = "/label-studio/files/extracted"
    LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT: str = "/label-studio/files"

    API_KEYS_FILE: str = "storage/secrets/api_keys.json"

    # MAX_ARCHIVE_SIZE_MB: int = 500

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @field_validator("LABEL_STUDIO_AUTH_SCHEME", mode="before")
    @classmethod
    def normalize_label_studio_auth_scheme(cls, value: object) -> str:
        if value is None or str(value).strip() == "":
            return "Token"

        scheme = str(value).strip().lower()
        if scheme == "bearer":
            return "Bearer"
        if scheme == "token":
            return "Token"

        return str(value)


settings = Settings()
