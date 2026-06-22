from pydantic_settings import BaseSettings, SettingsConfigDict


def get_settings() -> "Settings":
    return Settings()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    port: int = 8000
    arc_todo_api_base_url: str = "http://localhost:3000"
    arc_todo_username: str | None = None
    arc_todo_password: str | None = None
    arc_todo_access_token: str | None = None
    mcp_tool_settings_refresh_on_start: bool = True
    rag_api_base_url: str = "http://localhost:8020"
    rag_timeout_seconds: float = 30.0
    rag_top_k: int = 5
    rag_max_context_tokens: int = 4000


settings = get_settings()
