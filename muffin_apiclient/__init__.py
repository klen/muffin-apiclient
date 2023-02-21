"""Support session with Muffin framework."""

from typing import Optional

from muffin import Application
from muffin.plugins import BasePlugin

from apiclient import APIClient, TVMiddleware
from apiclient.api import HTTPDescriptor

__version__ = "3.6.0"
__project__ = "muffin-apiclient"
__author__ = "Kirill Klenov <horneds@gmail.com>"
__license__ = "MIT"


class Plugin(BasePlugin):

    """Make external API requests."""

    # Can be customized on setup
    name = "apiclient"
    root_url: Optional[str] = None
    timeout: Optional[int] = None

    defaults = {
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
        self.__api__ = None
        self.__client__ = None
        super().__init__(app, **options)

    def setup(self, app: Application, **options):
        """Setup API Client."""
        super().setup(app, **options)
        self.cfg.update(
            root_url=self.cfg.root_url or self.root_url,
            timeout=self.cfg.timeout or self.timeout,
        )
        self.__client__ = APIClient(
            self.cfg.root_url,
            timeout=self.cfg.timeout,
            backend_type=self.cfg.backend_type,
            backend_options=self.cfg.backend_options,
            raise_for_status=self.cfg.raise_for_status,
            read_response_body=self.cfg.read_response_body,
            parse_response_body=self.cfg.parse_response_body,
            **self.cfg.client_defaults
        )
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
