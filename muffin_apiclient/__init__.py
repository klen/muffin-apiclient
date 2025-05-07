"""Support session with Muffin framework."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Optional

from apiclient import APIClient, TVMiddleware
from muffin.plugins import BasePlugin

if TYPE_CHECKING:
    from apiclient.api import HTTPDescriptor
    from muffin import Application


class Plugin(BasePlugin):

    """Make external API requests."""

    # Can be customized on setup
    name = "apiclient"
    root_url: Optional[str] = None
    timeout: Optional[int] = None

    defaults: ClassVar = {
        # Root URL (https://api.github.com)
        "root_url": None,
        # APIClient Backend (httpx|aiohttp)
        "backend_type": "httpx",
        "backend_options": {},
        # Default client timeout
        "timeout": None,
        "raise_for_status": True,
        "read_response_body": True,
        "parse_response_body": True,
        # Client defaults (auth, headers)
        "client_defaults": {},
    }

    def __init__(self, app: Optional[Application] = None, **options):
        """Initialize plugin."""
        self.__api__: Optional[HTTPDescriptor] = None
        self.__client__: Optional[APIClient] = None
        super().__init__(app, **options)

    def setup(self, app: Application, **options):
        """Setup API Client."""
        super().setup(app, **options)
        cfg = self.cfg
        cfg.update(
            root_url=cfg.root_url or self.root_url,
            timeout=cfg.timeout or self.timeout,
        )
        client_params = {
            "timeout": cfg.timeout,
            "backend_type": cfg.backend_type,
            "backend_options": cfg.backend_options,
            "raise_for_status": cfg.raise_for_status,
            "read_response_body": cfg.read_response_body,
            "parse_response_body": cfg.parse_response_body,
        }
        client_params.update(cfg.client_defaults)

        self.__client__ = APIClient(cfg.root_url, **client_params)
        self.__api__ = self.__client__.api

    @property
    def client(self) -> APIClient:
        """Return client instance."""
        if self.__client__ is None:
            raise RuntimeError("Plugin is not initialized")
        return self.__client__

    @property
    def api(self) -> HTTPDescriptor:
        """Return client instance."""
        if self.__api__ is None:
            raise RuntimeError("Plugin is not initialized")
        return self.__api__

    async def startup(self):
        """Startup self client."""
        await self.client.startup()

    async def shutdown(self):
        """Shutdown self client."""
        await self.client.shutdown()

    def client_middleware(self, fn: TVMiddleware) -> TVMiddleware:
        """Register a middleware."""
        return self.client.middleware(fn)

    def request(self, method: str, url: str, **options):
        """Make a request."""
        return self.client.request(method, url, **options)
