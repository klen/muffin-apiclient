Muffin-APIClient
#################

.. _description:

**Muffin-APIClient** -- Its a plugin for Muffin_ framework which provides support
for external APIs

.. _badges:

.. image:: https://github.com/klen/muffin-apiclient/workflows/tests/badge.svg
    :target: https://github.com/klen/muffin-apiclient/actions
    :alt: Tests Status

.. image:: https://img.shields.io/pypi/v/muffin-apiclient
    :target: https://pypi.org/project/muffin-apiclient/
    :alt: PYPI Version

.. image:: https://img.shields.io/pypi/pyversions/muffin-apiclient
    :target: https://pypi.org/project/muffin-apiclient/
    :alt: Python Versions

.. _contents:

.. contents::

.. _requirements:

Requirements
=============

- python >= 3.11

.. _installation:

Installation
=============

**Muffin-APIClient** should be installed using pip, with one of the supported
backend extras: ::

    pip install muffin-apiclient[httpx]

Or with aiohttp as the backend: ::

    pip install muffin-apiclient[aiohttp]

.. _usage:

Usage
=====

Initialize and setup the plugin:

.. code-block:: python

    import muffin
    import muffin_apiclient

    # Create Muffin Application
    app = muffin.Application('example')

    # Initialize the plugin
    # As alternative: apiclient = muffin_apiclient.Plugin(app, **options)
    apiclient = muffin_apiclient.Plugin()
    apiclient.setup(app, root_url='https://api.github.com')

``root_url`` is required: it is the base URL all requests are built from.


Requesting an API
-----------------

The plugin exposes the ``aio-apiclient`` proxy as ``plugin.api``. Path parts are
chained as attributes (or ``[...]`` items) and the last part selects the HTTP
method:

.. code-block:: python

    github = muffin_apiclient.Plugin(app, name='github', root_url='https://api.github.com')

    # GET https://api.github.com/repos/klen/muffin-apiclient
    repo = await github.api.repos.klen['muffin-apiclient'].get()
    print(repo)  # dict parsed from the response JSON

Every attribute/``__getitem__`` appends one URL segment (surrounding slashes are
stripped), and ``root_url`` is joined with them. So the example above builds
``GET {root_url}/repos/klen/muffin-apiclient``. Use the item syntax when a
segment contains dots or slashes, and one of ``get``, ``post``, ``put``,
``patch``, ``delete``, ``head``, ``options`` as the last call:

.. code-block:: python

    slack = muffin_apiclient.Plugin(app, name='slack', root_url='https://slack.com/api')

    # POST https://slack.com/api/users.profile.set
    await slack.api['users.profile.set'].post(
        json={'profile': {'status_text': 'working', 'status_emoji': ':computer:'}},
        read_response_body=False,
    )

Any keyword argument of the call is passed to the backend request (``json``,
``data``, ``params``, ``headers``, ...), together with the plugin defaults.

What a call returns depends on two options:

- ``parse_response_body=True`` (default): the body is parsed by the response
  content type (``application/json`` gives a Python object, anything else gives
  text).
- ``read_response_body=False``: the body is not read and the backend response
  object (``httpx.Response`` or ``aiohttp.ClientResponse``) is returned, which
  is what you want when you don't care about the answer.

There is also a low level API on the plugin itself:

.. code-block:: python

    # Same client, but with an explicit method and URL
    await github.request('GET', '/test')

    # Register a middleware: (method, url, options) -> (method, url, options)
    @github.client_middleware
    async def add_token(method, url, options):
        options.setdefault('headers', {})['Authorization'] = 'token OAUTH-TOKEN'
        return method, url, options


Multiple clients
----------------

Pass ``name`` to register more than one client on the same application. The
plugin is available as ``app.plugins[name]``:

.. code-block:: python

    github = muffin_apiclient.Plugin(app, name='github', root_url='https://api.github.com')
    slack = muffin_apiclient.Plugin(app, name='slack', root_url='https://slack.com/api')

    assert app.plugins['github'] is github

The ``name`` also defines the configuration prefix (see below), so the clients
can be configured independently.

Options
-------

=========================== =========================== ===========================
Name                        Default value               Description
--------------------------- --------------------------- ---------------------------
**root_url**                ``None``                    Define general root URL for the client (required)
**timeout**                 ``10``                      Request timeout in seconds
**backend_type**            ``httpx``                   APIClient backend (``httpx``|``aiohttp``)
**backend_options**         ``{}``                      Options for the backend client
**raise_for_status**        ``True``                    Raise errors for HTTP statuses (4xx/5xx)
**read_response_body**      ``True``                    Read responses
**parse_response_body**     ``True``                    Parse responses (load json, etc)
**client_defaults**         ``{}``                      Default client values (headers, auth, etc)
=========================== =========================== ===========================

Unknown option names are ignored.

You are able to provide the options when you are initiliazing the plugin:

.. code-block:: python

    apiclient.setup(app, root_url='https://api.github.com')

.. note::

    Default request values (headers, auth, ``params``...) belong to
    ``client_defaults``, not to the plugin options themselves:

    .. code-block:: python

        github = muffin_apiclient.Plugin(app, name='github', root_url='https://api.github.com',
                                         client_defaults={
                                             'headers': {'Authorization': 'token OAUTH-TOKEN'},
                                         })

Backends
--------

Two backends are supported and both are optional dependencies:

- ``httpx`` (default) -- requires the ``httpx`` extra
- ``aiohttp`` -- requires the ``aiohttp`` extra

``backend_options`` are passed to the backend client constructor, so they are
``httpx.AsyncClient`` options for httpx and ``aiohttp.ClientSession`` options for
aiohttp:

.. code-block:: python

    github = muffin_apiclient.Plugin(app, name='github', root_url='https://api.github.com',
                                     backend_type='httpx',
                                     backend_options={'follow_redirects': True})

The backend is started and stopped together with the application (``startup``
and ``shutdown`` hooks), so the client is ready inside handlers.


Configuration
-------------

Options can be set on ``Muffin.Application`` itself. The plugin reads the
``{PLUGIN_NAME}_`` prefix, so for a plugin named ``apiclient`` (the default) and
for ``name='github'``:

.. code-block:: python

   APICLIENT_ROOT_URL = 'https://api.github.com'
   GITHUB_ROOT_URL = 'https://api.github.com'

``Muffin.Application`` configuration options are case insensitive.

Environment variables use the ``{CFG.NAME}_{PLUGIN_NAME}_`` prefix, where
``CFG.NAME`` is the application config name (``muffin`` by default). Complex
values (``backend_options``, ``client_defaults``) are parsed as JSON:

.. code-block:: bash

   export MUFFIN_APICLIENT_ROOT_URL=https://api.github.com
   export MUFFIN_GITHUB_CLIENT_DEFAULTS='{"headers": {"Authorization": "token OAUTH-TOKEN"}}'

Precedence (lowest to highest): plugin defaults, application config, options
passed to the plugin, environment variables.


Errors
------

With ``raise_for_status=True`` (the default) any 4xx/5xx response raises an
error of the backend (``httpx.HTTPStatusError`` or
``aiohttp.ClientResponseError``, both inherit from ``plugin.client.Error``).
Pass ``raise_for_status=False`` to get the parsed body/response anyway.

Redirects (3xx) are not errors: ``httpx`` does not follow them by default
(enable with ``backend_options={'follow_redirects': True}``), while ``aiohttp``
follows redirects for ``GET`` requests by default.

With ``parse_response_body=True`` a body which is not valid JSON is handled
differently by the backends: ``aiohttp`` falls back to the response text, while
``httpx`` raises ``json.JSONDecodeError``. Empty bodies (``204``) with a JSON
content type also raise for ``httpx`` -- use ``read_response_body=False`` (or a
different ``backend_type``) if an endpoint answers like that.


.. _bugtracker:

Bug tracker
===========

If you have any suggestions, bug reports or
annoyances please report them to the issue tracker
at https://github.com/klen/muffin-apiclient/issues

.. _contributing:

Contributing
============

Development of Muffin-APIClient happens at: https://github.com/klen/muffin-apiclient


Contributors
=============

* klen_ (Kirill Klenov)

.. _license:

License
========

Licensed under a `MIT license`_.

.. _links:


.. _klen: https://github.com/klen
.. _Muffin: https://github.com/klen/muffin

.. _MIT license: http://opensource.org/licenses/MIT
