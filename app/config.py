from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BOT_TOKEN: str
    SUPER_ADMIN_ID: int
    DATABASE_URL: str
    REDIS_URL: str
    CACHE_TTL: int = 1800
    TIMEZONE: str = "Europe/Kiev"

    class Config:
        env_file = ".env"


settings = Settings()
