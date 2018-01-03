import logging
import asyncio

from sanic import Sanic
from sanic import response

from gw import Bridge

import api.basic
import api.users
import api.auth

logging.basicConfig(level=logging.DEBUG)

app = Sanic(__name__)
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


def main():
    """Main entrypoint"""
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
