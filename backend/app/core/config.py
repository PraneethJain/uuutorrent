from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    QBITTORRENT_HOST: str
    QBITTORRENT_USER: str | None = None
    QBITTORRENT_PASS: str | None = None

    NYAA_RSS_URL: str = "https://nyaa.si/?page=rss"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
