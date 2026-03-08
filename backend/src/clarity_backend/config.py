import os

from pydantic_settings import BaseSettings

# Skip reading .env directly when dotenvx has already injected decrypted env vars,
# or when the .env contains encrypted values pydantic can't parse.
def _should_read_env_file() -> str | None:
    if os.getenv("DOTENV_CONFIG"):
        return None
    env_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")
    try:
        with open(env_path) as f:
            for line in f:
                if line.strip().startswith("#") or "=" not in line:
                    continue
                if "encrypted:" in line:
                    return None
    except OSError:
        pass
    return ".env"


_env_file = _should_read_env_file()


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./clarity.db"
    PLANE_API_KEY: str = ""
    PLANE_WORKSPACE_SLUG: str = ""
    PLANE_PROJECT_ID: str = ""
    PLANE_API_URL: str = "https://app.plane.so/api/v1"
    OPENAI_API_KEY: str = ""
    AIKIDO_WEBHOOK_SECRET: str = ""
    POSTHOG_API_KEY: str = ""
    POSTHOG_PROJECT_ID: str = ""
    POSTHOG_HOST: str = "https://eu.posthog.com"
    POSTHOG_POLL_INTERVAL: int = 60
    CORS_ORIGINS: str = '["*"]'

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS from JSON string or comma-separated values."""
        import json

        v = self.CORS_ORIGINS
        try:
            parsed = json.loads(v)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
        return [s.strip() for s in v.split(",") if s.strip()]

    # Google / Gmail OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8070/auth/google/callback"
    GOOGLE_CLOUD_PROJECT_ID: str = ""

    # Microsoft / Outlook OAuth
    MS_CLIENT_ID: str = ""
    MS_CLIENT_SECRET: str = ""
    MS_TENANT_ID: str = ""
    MS_REDIRECT_URI: str = "http://localhost:8070/auth/microsoft/callback"

    # Slack workspaces
    SLACK_WORKSPACE_1_BOT_TOKEN: str = ""
    SLACK_WORKSPACE_1_APP_TOKEN: str = ""
    SLACK_WORKSPACE_1_NAME: str = "Workspace 1"
    SLACK_WORKSPACE_2_BOT_TOKEN: str = ""
    SLACK_WORKSPACE_2_APP_TOKEN: str = ""
    SLACK_WORKSPACE_2_NAME: str = "Workspace 2"

    # Asana
    ASANA_ACCESS_TOKEN: str = ""
    ASANA_DEFAULT_WORKSPACE_GID: str = ""
    ASANA_DEFAULT_PROJECT_GID: str = ""

    model_config = {"env_file": _env_file}

    @property
    def slack_workspaces(self) -> list[dict]:
        workspaces = []
        if self.SLACK_WORKSPACE_1_BOT_TOKEN:
            workspaces.append(
                {
                    "name": self.SLACK_WORKSPACE_1_NAME,
                    "bot_token": self.SLACK_WORKSPACE_1_BOT_TOKEN,
                    "app_token": self.SLACK_WORKSPACE_1_APP_TOKEN,
                }
            )
        if self.SLACK_WORKSPACE_2_BOT_TOKEN:
            workspaces.append(
                {
                    "name": self.SLACK_WORKSPACE_2_NAME,
                    "bot_token": self.SLACK_WORKSPACE_2_BOT_TOKEN,
                    "app_token": self.SLACK_WORKSPACE_2_APP_TOKEN,
                }
            )
        return workspaces


settings = Settings()
