import muffin
import pytest
from unittest import mock
from apiclient.backends import BACKENDS


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

    assert isinstance(github.client.backend, BACKENDS[backend])


@mock.patch('apiclient.backends._httpx.BackendHTTPX.request', new_callable=mock.AsyncMock)
async def test_client(req, app):
    from muffin_apiclient import Plugin

    github = Plugin(app, name='github', root_url='https://api.github.com', backend='httpx')
    req.return_value = True

    res = await github.api.repos.klen.muffin()
    req.assert_awaited()
    req.assert_called_with(
        'GET', 'https://api.github.com/repos/klen/muffin',
        raise_for_status=True, read_response_body=True, parse_response_body=True)
    assert res
