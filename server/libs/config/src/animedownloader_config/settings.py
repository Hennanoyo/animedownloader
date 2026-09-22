from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = "development"
    database_url: str = (
        "postgresql+asyncpg://animedownloader:animedownloader@db:5432/animedownloader"
    )
    redis_url: str = "redis://redis:6379/0"
    storage_internal_url: str = "http://storage:8888"
    storage_public_url: str = "http://localhost:8888"
    cors_origins_raw: str = "http://localhost:5173"
    download_root: Path = Path("/data/downloads")
    media_root: Path = Path("/data/media")

    model_config = SettingsConfigDict(
        env_file="/app/server/.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins_raw.split(",")
            if origin.strip()
        ]
