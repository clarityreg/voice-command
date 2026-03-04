from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./clarity.db"
    PLANE_API_KEY: str = ""
    PLANE_WORKSPACE_SLUG: str = ""
    PLANE_PROJECT_ID: str = ""
    PLANE_API_URL: str = "https://app.plane.so/api/v1"
    AIKIDO_WEBHOOK_SECRET: str = ""
    CORS_ORIGINS: list[str] = ["*"]

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

    model_config = {"env_file": ".env"}

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
