from pydantic_settings import BaseSettings
from pydantic import AnyUrl

class Settings(BaseSettings):
    DB_URL: str
    REDIS_URL: str
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"  # relative path from src/zuriflow to project root
        env_file_encoding = "utf-8"

settings = Settings()
DB_URL = settings.DB_URL
REDIS_URL = settings.REDIS_URL
BROKER_URL = REDIS_URL
RESULT_BACKEND = REDIS_URL