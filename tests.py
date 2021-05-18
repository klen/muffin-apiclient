import muffin
import pytest
from unittest import mock
from apiclient.backends import BACKENDS


@pytest.fixture
def aiolib():
    return ('asyncio', {'use_uvloop': False})


@pytest.fixture
def app():
    return muffin.Application(DEBUG=True)


@pytest.mark.parametrize('backend', BACKENDS)
def test_base(app, backend):
    from muffin_apiclient import Plugin

    github = Plugin(app, name='github', root_url='https://api.github.com', backend=backend)
    assert github
    assert github.client
    assert github.api
    assert github.name == 'github'

    assert isinstance(github.client.backend, BACKENDS[backend])


@mock.patch('apiclient.backends._httpx.BackendHTTPX.request', new_callable=mock.AsyncMock)
async def test_client(req, app):
    from muffin_apiclient import Plugin

    class Github(Plugin):

        name = 'github'

        def setup(self, app, **options):
            super().setup(app, **options)

            @self.client_middleware
            async def md(method, url, options):
                options.setdefault('headers', {})
                options['headers']['x-token'] = 'TESTS'
                return method, url, options

    github = Github(app, root_url='https://api.github.com', backend='httpx')
    assert github.client
    assert github.api

    req.return_value = True

    res = await github.api.repos.klen.muffin()
    assert res
    req.assert_awaited()
    req.assert_called_with(
        'GET', 'https://api.github.com/repos/klen/muffin', headers={'x-token': 'TESTS'},
        raise_for_status=True, read_response_body=True, parse_response_body=True)

    req.reset_mock()
    req.return_value = True

    res = await github.request('GET', '/test')
    assert res
    req.assert_awaited()
    req.assert_called_with(
        'GET', 'https://api.github.com/test', headers={'x-token': 'TESTS'},
        raise_for_status=True, read_response_body=True, parse_response_body=True)
