from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str
    DATABASE_URL: str
    API_BASE_URL: str = "http://expense_backend_dev:8000"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"

    model_config = {"env_file": ".env", "case_sensitive": True}


settings = Settings()
