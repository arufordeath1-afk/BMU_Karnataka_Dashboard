import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings:
    """
    Central config. DATABASE_URL defaults to a local SQLite file so the
    project runs out of the box with zero external services. Point it at
    Postgres in production, e.g.:
      postgresql+psycopg2://postgres:postgres@localhost:5432/india_post
    No code changes are needed elsewhere — SQLAlchemy handles both.
    """
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/india_post.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-me-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "*").split(",")


settings = Settings()
