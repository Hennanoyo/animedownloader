from pathlib import Path
from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = "development"
    database_url: str = (
        "postgresql+asyncpg://animedownloader:animedownloader@db:5432/animedownloader"
    )
    redis_url: str = "redis://redis:6379/0"
    storage_backend: Literal["local", "seaweedfs"] = "local"
    storage_internal_url: str = "http://storage:8888"
    storage_public_url: str = "http://localhost:8888"
    cors_origins_raw: str = "http://localhost:5173,http://127.0.0.1:5173"
    download_root: Path = Path("/downloads")
    media_root: Path = Path("/data/media")
    qbittorrent_url: str = "http://qbittorrent:8080"
    qbittorrent_api_key: SecretStr | None = None
    ffmpeg_timeout_seconds: float = 1800.0
    ffmpeg_video_encoder: Literal["auto", "libx265", "hevc_nvenc"] = "auto"

    model_config = SettingsConfigDict(
        env_file="/app/server/.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("ffmpeg_timeout_seconds")
    @classmethod
    def validate_ffmpeg_timeout(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("ffmpeg_timeout_seconds must be positive")
        return value

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins_raw.split(",") if origin.strip()]
