from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str
    DATABASE_URL: str
    API_BASE_URL: str  # Debe venir de .env, no hardcodeado
    SECRET_KEY: str
    ALGORITHM: str = "HS256"

    model_config = {"env_file": ".env", "case_sensitive": True}


settings = Settings()
