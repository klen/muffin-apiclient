# Muffin-APIClient

[![Tests](https://github.com/klen/muffin-apiclient/workflows/tests/badge.svg)](https://github.com/klen/muffin-apiclient/actions)
[![PyPI](https://img.shields.io/pypi/v/muffin-apiclient)](https://pypi.org/project/muffin-apiclient/)
[![Python versions](https://img.shields.io/pypi/pyversions/muffin-apiclient)](https://pypi.org/project/muffin-apiclient/)

A [Muffin](https://github.com/klen/muffin) plugin for talking to external HTTP APIs. It
wraps [aio-apiclient](https://github.com/klen/aio-apiclient) and adds application config,
lifecycle (startup/shutdown) and a typed response.

## Installation

Python 3.11+ is required. Install the plugin with one of the supported backends:

```bash
pip install muffin-apiclient[httpx]    # default backend
pip install muffin-apiclient[aiohttp]
```

## Quick start

```python
import muffin
import muffin_apiclient

app = muffin.Application("example")

apiclient = muffin_apiclient.Plugin(app, root_url="https://api.github.com")

# Or initialize later:
# apiclient = muffin_apiclient.Plugin()
# apiclient.setup(app, root_url="https://api.github.com")


async def handler():
    # GET https://api.github.com/repos/klen/muffin
    return await apiclient.api.repos.klen.muffin()
```

`root_url` is required: it is the base URL all requests are built from. The backend is
started and stopped together with the application, so the client is ready inside handlers.

## Making requests

`plugin.api` builds a request from chained path parts. Every attribute or `[...]` item
appends one URL segment (surrounding slashes are stripped); the last part selects the HTTP
method when it names one (`get`, `post`, `put`, `patch`, `delete`, `head`, `options`):

```python
github = muffin_apiclient.Plugin(app, name="github", root_url="https://api.github.com")

# GET https://api.github.com/repos/klen/muffin
repo = await github.api.repos.klen.muffin.get()

# POST https://api.github.com/repos/klen/muffin
await github.api.repos.klen.muffin.post(json={"private": False})
```

Without a method segment the request is `GET`. Use the item syntax for segments with dots
or slashes:

```python
slack = muffin_apiclient.Plugin(app, name="slack", root_url="https://slack.com/api")

# POST https://slack.com/api/users.profile.set
await slack.api["users.profile.set"].post(
    json={"profile": {"status_text": "working", "status_emoji": ":computer:"}},
    read_response_body=False,
)
```

The descriptor is immutable: a partially built path can be stored and reused, and each
call leaves it unchanged:

```python
repo = github.api.repos.klen.muffin
await repo.get()
await repo.patch(json={"archived": True})  # PATCH https://api.github.com/repos/klen/muffin
```

A method-looking segment is only treated as a method when no method is passed explicitly,
so `method=` keeps it in the URL:

```python
await github.api.repos.delete()  # DELETE https://api.github.com/repos
await github.api.users.delete(method="GET")  # GET    https://api.github.com/users/delete
```

Any keyword argument is passed to the backend request (`json`, `data`, `params`,
`headers`, ...), together with the plugin defaults. A positional argument is sent as
`data` (not `json`):

```python
await github.api.repos.post({"name": "example"})  # data={"name": "example"}
await github.api.repos.post(json={"name": "example"})
```

Requests are always relative to `root_url` except absolute URLs:

```python
await github.request("GET", "https://example.com/ping")
```

What a call returns depends on two options:

- `parse_response_body=True` (default): the body is parsed by the response content type
  (`application/json` gives a Python object, anything else gives text).
- `read_response_body=False`: the body is not read and the backend response object
  (`httpx.Response` or `aiohttp.ClientResponse`) is returned, which is what you want when
  you don't care about the answer.

Both are client-wide defaults, and both can be overridden per request.

## Typing

The package ships a `py.typed` marker, the plugin is generic over the response type and
its options are described by `PluginOptions`, so a type checker rejects unknown options
and wrong value types:

```python
from typing import Any

import muffin_apiclient

github = muffin_apiclient.Plugin[dict[str, Any]](
    app, name="github", root_url="https://api.github.com"
)

repo: dict[str, Any] = await github.api.repos.klen.muffin()
```

## Multiple clients

Pass `name` to register more than one client on the same application. The plugin is
available as `app.plugins[name]`:

```python
github = muffin_apiclient.Plugin(app, name="github", root_url="https://api.github.com")
slack = muffin_apiclient.Plugin(app, name="slack", root_url="https://slack.com/api")

assert app.plugins["github"] is github
```

The `name` also defines the configuration prefix (see below), so the clients can be
configured independently.

## Middleware

A middleware can rewrite the method, the URL and the request options. Middlewares run in
registration order, after the client defaults are merged into the options:

```python
@github.client_middleware
async def add_token(method, url, options):
    options.setdefault("headers", {})["Authorization"] = "token OAUTH-TOKEN"
    return method, url, options
```

Register the middleware before the first request, e.g. right after the plugin setup.

## Client

`plugin.client` is the underlying `apiclient.APIClient` instance. Use it for the features
this plugin does not wrap, e.g. its `defaults`, `middlewares`, `Error` and `root`:

```python
await github.request("GET", "/test")  # a shortcut for github.client.request(...)
assert github.client.root == "https://api.github.com"
```

## Options

| Name                  | Default | Description                                |
| --------------------- | ------- | ------------------------------------------ |
| `root_url`            | `None`  | Root URL for the client (required)         |
| `timeout`             | `10`    | Request timeout in seconds                 |
| `backend_type`        | `httpx` | APIClient backend (`httpx` or `aiohttp`)   |
| `backend_options`     | `{}`    | Options for the backend client             |
| `raise_for_status`    | `True`  | Raise errors for HTTP statuses (4xx/5xx)   |
| `read_response_body`  | `True`  | Read responses                             |
| `parse_response_body` | `True`  | Parse responses (load JSON, etc)           |
| `client_defaults`     | `{}`    | Default client values (headers, auth, etc) |
| `disabled`            | `False` | Skip the plugin setup (the plugin is not registered) |

Unknown option names are ignored. The options can be passed on init or on setup:

```python
apiclient.setup(app, root_url="https://api.github.com")
```

**Note:** default request values (headers, auth, `params`, ...) belong to
`client_defaults`, not to the plugin options themselves:

```python
github = muffin_apiclient.Plugin(
    app,
    name="github",
    root_url="https://api.github.com",
    client_defaults={"headers": {"Authorization": "token OAUTH-TOKEN"}},
)
```

`client_defaults` is merged into the client parameters last, so a key which names a
client parameter (`timeout`, `raise_for_status`, ...) overrides it.

## Backends

Two backends are supported and both are optional dependencies:

- `httpx` (default): requires the `httpx` extra
- `aiohttp`: requires the `aiohttp` extra

`backend_options` are passed to the backend client constructor, so they are
`httpx.AsyncClient` options for httpx and `aiohttp.ClientSession` options for aiohttp:

```python
github = muffin_apiclient.Plugin(
    app,
    name="github",
    root_url="https://api.github.com",
    backend_type="httpx",
    backend_options={"follow_redirects": True},
)
```

## Configuration

Options can be set on `Muffin.Application` itself. The plugin reads the `{PLUGIN_NAME}_`
prefix, so for a plugin named `apiclient` (the default) and for `name="github"`:

```python
APICLIENT_ROOT_URL = "https://api.github.com"
GITHUB_ROOT_URL = "https://api.github.com"
```

`Muffin.Application` configuration options are case insensitive.

Environment variables use the `{CFG.NAME}_{PLUGIN_NAME}_` prefix, where `CFG.NAME` is the
application config name (`muffin` by default). Complex values (`backend_options`,
`client_defaults`) are parsed as JSON:

```bash
export MUFFIN_APICLIENT_ROOT_URL=https://api.github.com
export MUFFIN_GITHUB_CLIENT_DEFAULTS='{"headers": {"Authorization": "token OAUTH-TOKEN"}}'
```

Precedence (lowest to highest): plugin defaults, application config, options passed to
the plugin, environment variables.

## Errors

With `raise_for_status=True` (the default) any 4xx/5xx response raises an error of the
backend (`httpx.HTTPStatusError` or `aiohttp.ClientResponseError`, both inherit from
`plugin.client.Error`). Pass `raise_for_status=False` to get the parsed body/response
anyway:

```python
try:
    await github.api.repos.klen.muffin()
except github.client.Error:
    ...
```

Redirects (3xx) are not errors: `httpx` does not follow them by default (enable with
`backend_options={"follow_redirects": True}`), while `aiohttp` follows redirects for
`GET` requests by default.

With `parse_response_body=True` a body which is not valid JSON is handled differently by
the backends: `aiohttp` falls back to the response text, while `httpx` raises
`json.JSONDecodeError`. Empty bodies (`204`) with a JSON content type also raise for
`httpx`: use `read_response_body=False` (or a different `backend_type`) if an endpoint
answers like that.

## Development

```bash
make        # install dependencies and pre-commit hooks (uv sync)
make test   # pytest tests.py
make lint   # pyrefly + ruff
```

## Contributing

Development of Muffin-APIClient happens at
https://github.com/klen/muffin-apiclient. Bug reports and pull requests are welcome.

## License

Licensed under the [MIT license](http://opensource.org/licenses/MIT).

---

Maintained by [klen](https://github.com/klen). See also
[Muffin](https://github.com/klen/muffin) and [aio-apiclient](https://github.com/klen/aio-apiclient).
