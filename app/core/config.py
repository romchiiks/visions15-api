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

    S3_ENDPOINT_URL: str = "minio:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET: str = "visions15-datasets"
    S3_SECURE: bool = False
    S3_PUBLIC_BASE_URL: str = "http://localhost:9000/visions15-datasets"
    S3_BUCKET_PUBLIC_READ: bool = True
    MODEL_S3_BUCKET: str = "visions15-models"
    MODEL_S3_PREFIX: str = "model"

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
