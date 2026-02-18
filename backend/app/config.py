from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = (
        "postgresql+asyncpg://smartdocs:smartdocs@localhost:5432/smartdocs"
    )

    # Azure Document Intelligence
    AZURE_DI_ENDPOINT: str = ""
    AZURE_DI_KEY: str = ""
    AZURE_DI_MODEL_ID: str = "prebuilt-document"

    # Azure OpenAI
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_KEY: str = ""
    AZURE_OPENAI_DEPLOYMENT: str = "gpt-4o"
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str = "text-embedding-3-small"

    # JWT
    JWT_SECRET: str = "change-this-to-a-random-secret-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480

    # File storage
    UPLOAD_DIR: str = "/tmp/uploads"

    # Azure Storage
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    AZURE_STORAGE_CONTAINER_NAME: str = "documents"


settings = Settings()
