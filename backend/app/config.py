from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    host: str = "0.0.0.0"
    port: int = 8000
    data_dir: str = "data"
    max_file_mb: int = 50

    name_match_threshold: int = 90
    name_review_threshold: int = 70
    amount_tolerance: float = 1.0

    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
