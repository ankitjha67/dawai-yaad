"""Dawai Yaad — Application Configuration."""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = "Dawai Yaad"
    app_version: str = "1.0.0"
    environment: str = "development"
    cors_origins: str = "http://localhost:3000,http://localhost:8080"

    # Database
    db_user: str = "dawai"
    db_pass: str = "dawai_secret_2025"
    db_host: str = "db"
    db_port: int = 5432
    db_name: str = "dawai_yaad"

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def database_url_sync(self) -> str:
        return f"postgresql://{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/{self.db_name}"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # JWT
    secret_key: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours
    refresh_token_expire_days: int = 30

    # Firebase
    fcm_server_key: str = ""
    fcm_project_id: str = ""

    # MinIO
    minio_endpoint: str = "minio:9000"
    minio_user: str = "dawai_minio"
    minio_pass: str = "dawai_minio_secret"
    minio_bucket: str = "dawai-documents"
    minio_secure: bool = False

    # OTP
    msg91_auth_key: str = ""
    msg91_template_id: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
