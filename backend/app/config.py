from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Berth API"
    database_url: str = "postgresql+psycopg://taskboard:taskboard@localhost:5432/taskboard"
    cors_origins: str = "*"
    deploy_report_token: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
