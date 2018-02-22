import logging
import asyncio

from sanic import Sanic
from sanic import response

from gw import Bridge

import api.basic
import api.users
import api.auth
from api.errors import ApiError, LitecordValidationError

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)
app = Sanic(__name__)

# load blueprints
app.blueprint(api.basic.bp)
app.blueprint(api.users.bp)
app.blueprint(api.auth.bp)

API_PREFIXES = [
    '/api/v6',
    '/api/v7'
]


@app.route('/')
async def index(request):
    """Give index page"""
    return response.text('Welcome to litecord!')


@app.exception(LitecordValidationError)
async def handle_lv(request, exception):
    """Handle bad payloads."""
    log.warning(f'Validation error: {exception!r}')
    return response.json({
        'code': 0,
        'message': exception.args[0],
        'val_err': exception.args[1],
    }, status=exception.status_code)


@app.exception(ApiError)
def handle_api_error(request, exception):
    """Handle any kind of application-level raised error.
    """
    log.warning(f'API error: {exception!r}')
    return response.json({
        'code': exception.api_errcode,
        'message': exception.args[0],
    }, status=exception.status_code)


@app.exception(Exception)
def handle_exception(request, exception):
    """Handle a general exception in the API."""
    log.exception('error in request')
    return response.json({
        'code': 0,
        'message': repr(exception)
    }, status=500)


def main():
    """Main entrypoint"""

    # this is a hack to make /api, /api/v6 and /api/v7
    # route to the same shit
    for uri in list(app.router.routes_all.keys()):
        if not uri.startswith('/api'):
            continue

        for prefix in API_PREFIXES:
            handler = app.router.routes_all[uri].handler
            replaced = uri.replace('/api', prefix)

            if not app.router.routes_all.get(replaced):
                app.add_route(handler, replaced)

    server = app.create_server(host="0.0.0.0", port=8000)
    loop = asyncio.get_event_loop()
    bridge = Bridge(app, server, loop)
    try:
        asyncio.ensure_future(bridge.init())
        loop.run_forever()
    except Exception:
        loop.stop()

if __name__ == '__main__':
    main()
