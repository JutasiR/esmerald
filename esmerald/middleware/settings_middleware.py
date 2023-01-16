import inspect
from typing import TYPE_CHECKING

from esmerald.conf.global_settings import EsmeraldAPISettings
from esmerald.exceptions import ImproperlyMiddlewareConfigured
from esmerald.protocols.middleware import MiddlewareProtocol
from esmerald.types import ASGIApp, Receive, Scope, Send


class SettingsMiddleware(MiddlewareProtocol):
    def __init__(self, app: "ASGIApp", settings: "EsmeraldAPISettings"):
        """Settings Middleware class.

        Args:
            app: The 'next' ASGI app to call.
            settings: An instance of a EsmeraldAPISettings or a subclass.
        """
        super().__init__(app)
        self.app = app
        self.settings = settings

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        app_settings = None

        if not isinstance(self.settings, EsmeraldAPISettings):
            raise ImproperlyMiddlewareConfigured(
                "The settings should be an instance or a subclass of EsmeraldAPISettings"
            )

        app_settings = self.settings
        scope["settings"] = app_settings
        await self.app(scope, receive, send)
