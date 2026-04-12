from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Career Planning Agent"
    app_env: str = "development"
    debug: bool = Field(default=False, validation_alias="APP_DEBUG")
    api_prefix: str = "/api/v1"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8001
    frontend_url: str = "http://localhost:3000"
    skip_db_check: bool = False
    demo_auto_seed_job_profiles: bool = False
    demo_job_seed_path: str = "/app/data/seeds/job_postings_sample.csv"

    postgres_server: str = "db"
    postgres_port: int = 5432
    postgres_db: str = "career_planning"
    postgres_user: str = "career_planning"
    postgres_password: str = "career_planning"

    log_level: str = "INFO"
    job_profile_llm_provider: str = "heuristic"
    job_profile_llm_base_url: str | None = None
    job_profile_llm_api_key: str | None = None
    job_profile_llm_model: str = "job-profile-extractor"
    job_profile_llm_timeout_seconds: int = 30
    reporting_llm_provider: str | None = None
    reporting_llm_base_url: str | None = None
    reporting_llm_api_key: str | None = None
    reporting_llm_model: str | None = None
    reporting_llm_timeout_seconds: int | None = None
    assistant_llm_provider: str | None = None
    assistant_llm_base_url: str | None = None
    assistant_llm_api_key: str | None = None
    assistant_llm_model: str | None = None
    assistant_llm_timeout_seconds: int | None = None
    job_profile_batch_limit: int = 50
    job_profile_extractor_version: str = "v1"

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @computed_field  # type: ignore[misc]
    @property
    def database_url(self) -> str:
        return (
            "postgresql+asyncpg://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_server}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field  # type: ignore[misc]
    @property
    def cors_origins(self) -> list[str]:
        return [self.frontend_url]


@lru_cache
def get_settings() -> Settings:
    return Settings()
