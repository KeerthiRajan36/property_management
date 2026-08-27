from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- App ---
    APP_NAME: str = "Smart Property & Facility Management Platform"
    API_V1_PREFIX: str = "/api/v1"
    ENV: str = "development"
    DEBUG: bool = True

    # --- Database ---
    # Default: local SQLite file, no external DB required to run the project.
    # For Postgres set: postgresql+psycopg2://user:pass@host:5432/dbname
    DATABASE_URL: str = "sqlite:///./property_management.db"

    # --- Auth / JWT ---
    SECRET_KEY: str = "CHANGE_ME_super_secret_key_please_override_in_env"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- Rate limiting ---
    RATE_LIMIT_DEFAULT: str = "100/minute"

    # --- CORS ---
    CORS_ORIGINS: str = "*"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
