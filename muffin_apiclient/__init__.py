"""Muffin plugin which provides a typed client for external HTTP APIs."""

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    ClassVar,
    Generic,
    Optional,
    Protocol,
    TypedDict,
    TypeVar,
    Unpack,
    cast,
)

from apiclient import APIClient
from apiclient.types import TMiddleware
from muffin.plugins import BasePlugin

if TYPE_CHECKING:
    from collections.abc import Mapping

    from apiclient.api import HTTPDescriptor
    from apiclient.backends import ABCBackend
    from muffin import Application


TResponse = TypeVar("TResponse")
TClientMiddleware = TypeVar("TClientMiddleware", bound=TMiddleware)


class PluginOptions(TypedDict, total=False):
    """Options of the plugin.

    The same names are read from the application config and from the environment under the
    plugin prefix (case insensitive).
    """

    # Root URL (https://api.github.com)
    root_url: str | None
    # APIClient Backend (httpx|aiohttp)
    backend_type: str | type[ABCBackend]
    backend_options: dict[str, Any]
    # Default client timeout
    timeout: float
    raise_for_status: bool
    read_response_body: bool
    parse_response_body: bool
    # Client defaults (auth, headers)
    client_defaults: dict[str, Any]
    disabled: bool


class _Config(Protocol):
    """Typed view of the plugin config (modconfig keeps its values untyped)."""

    root_url: str | None
    backend_type: str | type[ABCBackend]
    backend_options: dict[str, Any]
    timeout: float
    raise_for_status: bool
    read_response_body: bool
    parse_response_body: bool
    client_defaults: dict[str, Any]


class Plugin(BasePlugin, Generic[TResponse]):
    """Make external API requests.

    The plugin configures an `apiclient.APIClient` from the application config and starts it
    with the application. Parameterize it with the type your backend returns, e.g.:

        github = Plugin[dict[str, Any]](app, name="github", root_url="https://api.github.com")
        repo = await github.api.repos.klen.muffin()
    """

    # Can be customized on setup
    name = "apiclient"

    # A mapping, not a TypedDict: BasePlugin allows any mapping to be written here
    defaults: ClassVar[Mapping[str, Any]] = cast(
        "PluginOptions",
        {
            "root_url": None,
            "backend_type": "httpx",
            "backend_options": {},
            "timeout": 10,
            "raise_for_status": True,
            "read_response_body": True,
            "parse_response_body": True,
            "client_defaults": {},
        },
    )

    def __init__(
        self,
        app: Optional[Application] = None,
        *,
        name: Optional[str] = None,
        **options: Unpack[PluginOptions],
    ) -> None:
        """Initialize plugin."""
        self.__api__: Optional[HTTPDescriptor[TResponse]] = None
        self.__client__: Optional[APIClient[TResponse]] = None
        super().__init__(app, name=name, **options)

    def setup(
        self,
        app: Application,
        *,
        name: Optional[str] = None,
        **options: Unpack[PluginOptions],
    ) -> bool:
        """Set up the client from the options and the application config."""
        if not super().setup(app, name=name, **options):
            return False

        cfg = cast("_Config", self.cfg)
        root_url = cfg.root_url
        if not root_url:
            raise ValueError(f"{self.name}: root_url is required")

        client_params: dict[str, Any] = {
            "timeout": cfg.timeout,
            "backend_type": cfg.backend_type,
            "backend_options": cfg.backend_options,
            "raise_for_status": cfg.raise_for_status,
            "read_response_body": cfg.read_response_body,
            "parse_response_body": cfg.parse_response_body,
        }
        client_params.update(cfg.client_defaults)

        self.__client__ = APIClient(root_url, **client_params)
        self.__api__ = self.__client__.api
        return True

    @property
    def client(self) -> APIClient[TResponse]:
        """Return the `apiclient.APIClient` instance."""
        if self.__client__ is None:
            raise RuntimeError("Plugin is not initialized")
        return self.__client__

    @property
    def api(self) -> HTTPDescriptor[TResponse]:
        """Return the descriptor to build API requests."""
        if self.__api__ is None:
            raise RuntimeError("Plugin is not initialized")
        return self.__api__

    async def startup(self) -> None:
        """Start the client backend."""
        await self.client.startup()

    async def shutdown(self) -> None:
        """Stop the client backend."""
        await self.client.shutdown()

    def client_middleware(self, fn: TClientMiddleware) -> TClientMiddleware:
        """Register a client middleware (can be used as a decorator)."""
        return self.client.middleware(fn)

    def request(self, method: str, url: str, **options: Any) -> Awaitable[TResponse]:
        """Make a request to a path or to an absolute URL."""
        return self.client.request(method, url, **options)
