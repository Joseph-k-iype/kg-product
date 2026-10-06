from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")
    database_url: str = "postgresql+psycopg://knowledge:knowledge-local@localhost:55432/knowledge"
    minio_endpoint: str = "localhost:59000"
    minio_access_key: str = "knowledge"
    minio_secret_key: str = "knowledge-local"
    minio_bucket: str = "knowledge-artifacts"
    graph_url: str = "redis://localhost:56379"
    model_cache: str = "./.model-cache"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


settings = Settings()
