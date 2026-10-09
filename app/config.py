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
    # arc-hub admin tools call the hub directly; the hub token is a server-side
    # secret and is never a tool argument or part of tool output.
    arc_hub_base_url: str | None = None
    arc_hub_token: str | None = None
    mcp_tool_settings_refresh_on_start: bool = True


settings = get_settings()
