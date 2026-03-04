import asyncio

from clarity_backend.notifications.models import Notification, Source


class ServiceRegistry:
    def __init__(self):
        self.services: list = []
        self.gmail_services: list = []
        self.outlook_services: list = []
        self.slack_services: list = []
        self.asana_service = None
        self.plane_service = None

    async def start_all(self):
        from sqlmodel.ext.asyncio.session import AsyncSession

        from clarity_backend.config import settings
        from clarity_backend.database import engine
        from clarity_backend.notifications.crud import get_accounts_by_service

        print("=" * 50)
        print("  CLARITY - Starting Notification Services")
        print("=" * 50)

        async with AsyncSession(engine) as session:
            # Gmail accounts from DB
            if settings.GOOGLE_CLIENT_ID:
                try:
                    from clarity_backend.services.gmail import GmailService

                    gmail_accounts = await get_accounts_by_service(session, "gmail")
                    for acct in gmail_accounts:
                        tokens = {
                            "access_token": acct["access_token"],
                            "refresh_token": acct["refresh_token"],
                        }
                        service = GmailService(acct["account"], credentials=tokens)
                        self.gmail_services.append(service)
                        self.services.append(service)
                        await service.start()
                except ImportError:
                    print("  [Gmail] google-auth not installed, skipping")

            # Outlook accounts from DB
            if settings.MS_CLIENT_ID:
                try:
                    from clarity_backend.services.outlook import OutlookService

                    outlook_accounts = await get_accounts_by_service(session, "outlook")
                    for acct in outlook_accounts:
                        tokens = {
                            "access_token": acct["access_token"],
                            "refresh_token": acct["refresh_token"],
                        }
                        service = OutlookService(acct["account"], credentials=tokens)
                        self.outlook_services.append(service)
                        self.services.append(service)
                        await service.start()
                except ImportError:
                    print("  [Outlook] msal not installed, skipping")

        # Slack workspaces
        for ws_config in settings.slack_workspaces:
            try:
                from clarity_backend.services.slack import SlackService

                service = SlackService(
                    workspace_name=ws_config["name"],
                    bot_token=ws_config["bot_token"],
                    app_token=ws_config["app_token"],
                )
                self.slack_services.append(service)
                self.services.append(service)
                await service.start()
            except ImportError:
                print("  [Slack] slack-sdk not installed, skipping")
                break

        # Asana
        if settings.ASANA_ACCESS_TOKEN:
            try:
                from clarity_backend.services.asana import AsanaService

                self.asana_service = AsanaService()
                self.services.append(self.asana_service)
                await self.asana_service.start()
            except ImportError:
                print("  [Asana] httpx not available, skipping")

        # Plane (notification feed -- separate from triage PlaneClient)
        if settings.PLANE_API_KEY and settings.PLANE_API_URL:
            try:
                from clarity_backend.services.plane_notifier import PlaneNotifierService

                self.plane_service = PlaneNotifierService()
                self.services.append(self.plane_service)
                await self.plane_service.start()
            except ImportError:
                print("  [Plane] notification service unavailable, skipping")

        print(f"  {len(self.services)} notification services initialized")
        print("=" * 50)

    async def add_gmail_service(self, email: str, tokens: dict):
        from clarity_backend.services.gmail import GmailService

        for existing in self.gmail_services:
            if existing.email == email:
                existing._credentials = tokens
                await existing.stop()
                await existing.start()
                return existing
        service = GmailService(email, credentials=tokens)
        self.gmail_services.append(service)
        self.services.append(service)
        await service.start()
        return service

    async def remove_gmail_service(self, email: str) -> bool:
        for svc in self.gmail_services:
            if svc.email == email:
                await svc.stop()
                self.gmail_services.remove(svc)
                self.services.remove(svc)
                return True
        return False

    async def add_outlook_service(self, email: str, tokens: dict):
        from clarity_backend.services.outlook import OutlookService

        for existing in self.outlook_services:
            if existing.email == email:
                existing._credentials = tokens
                await existing.stop()
                await existing.start()
                return existing
        service = OutlookService(email, credentials=tokens)
        self.outlook_services.append(service)
        self.services.append(service)
        await service.start()
        return service

    async def remove_outlook_service(self, email: str) -> bool:
        for svc in self.outlook_services:
            if svc.email == email:
                await svc.stop()
                self.outlook_services.remove(svc)
                self.services.remove(svc)
                return True
        return False

    async def stop_all(self):
        for service in self.services:
            await service.stop()

    async def fetch_all_recent(self, limit: int = 50) -> list[Notification]:
        all_notifications = []
        tasks = [s.fetch_recent(limit=10) for s in self.services]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, list):
                all_notifications.extend(result)
        all_notifications.sort(key=lambda n: n.timestamp, reverse=True)
        return all_notifications[:limit]

    def get_service_for_reply(self, source: Source, account: str):
        if source == Source.GMAIL:
            return next((s for s in self.gmail_services if s.email == account), None)
        elif source == Source.OUTLOOK:
            return next((s for s in self.outlook_services if s.email == account), None)
        elif source == Source.SLACK:
            return next((s for s in self.slack_services if s.workspace_name == account), None)
        return None


registry = ServiceRegistry()
