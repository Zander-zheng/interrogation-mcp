from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    deployment_url: str = "http://localhost:8123"
    langsmith_api_key: str = ""
    mcp_api_key: str = ""

    model_config = {"env_prefix": "", "env_file": ".env"}


settings = Settings()
