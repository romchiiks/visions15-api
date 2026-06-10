from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Visions15-API"
    APP_VERSION: str = "0.1.0"

    LABEL_STUDIO_URL: str
    LABEL_STUDIO_API_KEY: str

    UPLOAD_DIR: str = "/label-studio/files/uploads"
    EXTRACTED_DIR: str = "/label-studio/files/extracted"

    API_KEYS_FILE: str = "storage/secrets/api_keys.json"

    MAX_ARCHIVE_SIZE_MB: int = 500

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
