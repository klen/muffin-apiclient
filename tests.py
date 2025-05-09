import muffin
import pytest
from apiclient.backends import BACKENDS

# Support Python < 3.8
try:
    import mock  # type: ignore
except ImportError:
    from unittest import mock  # type: ignore


@pytest.fixture()
def aiolib():
    return ("asyncio", {"use_uvloop": False})


@pytest.fixture()
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

    class Github(Plugin):
        name = "github"
        root_url = "https://api.github.com"
        timeout = 20

        def setup(self, app, **options):
            super().setup(app, **options)

            @self.client_middleware
            async def md(method, url, options):
                options.setdefault("headers", {})
                options["headers"]["x-token"] = "TESTS"
                return method, url, options

    github = Github(app, backend_type="httpx")
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
