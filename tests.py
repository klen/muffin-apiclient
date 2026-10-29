from unittest import mock

import muffin
import pytest
from apiclient.backends import BACKENDS


@pytest.fixture
def aiolib():
    return "asyncio"


@pytest.fixture
def app():
    return muffin.Application(DEBUG=True)


@pytest.mark.parametrize("backend_type", BACKENDS)
def test_base(app, backend_type):
    from muffin_apiclient import Plugin

    github = Plugin(
        app,
        name="github",
        root_url="https://api.github.com",
        backend_type=backend_type,
    )
    assert github
    assert github.client
    assert github.api
    assert github.name == "github"

    assert isinstance(github.client.backend, BACKENDS[backend_type])


def test_setup(app):
    from muffin_apiclient import Plugin

    github = Plugin(
        app,
        name="github",
        root_url="https://api.github.com",
        client_defaults={
            "raise_for_status": False,
        },
    )
    assert github
    assert github.__client__
    assert github.__client__.raise_for_status is False


@mock.patch(
    "apiclient.backends._httpx.BackendHTTPX.request",
    new_callable=mock.AsyncMock,
)
async def test_client(req, app):
    from muffin_apiclient import Plugin

    github = Plugin(
        app,
        name="github",
        root_url="https://api.github.com",
        timeout=20,
        backend_type="httpx",
    )

    @github.client_middleware
    async def md(method, url, options):
        options.setdefault("headers", {})
        options["headers"]["x-token"] = "TESTS"
        return method, url, options

    assert github.client
    assert github.api
    assert github.cfg.root_url == "https://api.github.com"
    assert github.cfg.timeout == 20

    req.return_value = True

    res = await github.api.repos.klen.muffin()
    assert res
    req.assert_awaited()
    req.assert_called_with(
        "GET",
        "https://api.github.com/repos/klen/muffin",
        headers={"x-token": "TESTS"},
        raise_for_status=True,
        read_response_body=True,
        parse_response_body=True,
    )

    req.reset_mock()
    req.return_value = True

    res = await github.request("GET", "/test")
    assert res
    req.assert_awaited()
    req.assert_called_with(
        "GET",
        "https://api.github.com/test",
        headers={"x-token": "TESTS"},
        raise_for_status=True,
        read_response_body=True,
        parse_response_body=True,
    )


def test_required_root_url(app):
    from muffin_apiclient import Plugin

    with pytest.raises(ValueError, match="root_url is required"):
        Plugin(app, name="github")


def test_timeout(app):
    from muffin_apiclient import Plugin

    default = Plugin(app, name="default", root_url="https://api.github.com")
    assert default.client.backend.client.timeout.read == 10

    custom = Plugin(app, name="custom", root_url="https://api.github.com", timeout=7)
    assert custom.client.backend.client.timeout.read == 7


def test_disabled(app):
    from muffin_apiclient import Plugin

    plugin = Plugin(app, root_url="https://api.github.com", disabled=True)
    assert plugin.name not in app.plugins
    with pytest.raises(RuntimeError, match="not initialized"):
        _ = plugin.api


def test_config(app):
    from muffin_apiclient import Plugin

    app.cfg.update(APICLIENT_ROOT_URL="https://api.github.com")
    apiclient = Plugin(app)
    assert apiclient.cfg.root_url == "https://api.github.com"


def test_env_config(app, monkeypatch):
    from muffin_apiclient import Plugin

    monkeypatch.setenv("MUFFIN_GITHUB_ROOT_URL", "https://api.github.com")
    github = Plugin(app, name="github")
    assert github.cfg.root_url == "https://api.github.com"
    assert app.plugins["github"] is github
