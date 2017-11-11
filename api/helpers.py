import logging

from sanic import response
from sanic.exceptions import ServerError

log = logging.getLogger(__name__)


def get_token(request):
    prefixes = ('Bearer', 'Bot')
    raw = request.headers.get('Authorization')
    log.debug('raw: %s', raw)
    if not raw:
        return

    for prefix in prefixes:
        if raw.startswith(prefix):
            return raw.replace(prefix, '').strip()

    return raw


async def authorize(request):
    token = get_token(request)
    if not token:
        raise ServerError('Authorization not provided', status_code=401)

    # TODO: check token here
    log.info('token: %s', token)
    pass


def route(handler):
    async def new_handler(request, *args, **kwargs):
        br = request.app.bridge
        return await handler(br, request, *args, **kwargs)

    return new_handler


def auth_route(handler):
    async def new_handler(request, *args, **kwargs):
        br = request.app.bridge
        token = get_token(request)
        log.info('token: %s', token)

        if not token:
            return response.json({
                'code': 0,
                'message': '401: Unauthorized'
            }, status=401)

        ok, user_id = await br.token_valid(token)
        if not ok:
            return response.json({
                'code': 0,
                'message': 'User not found [id]'
            }, status=401)

        user = await br.get_user(user_id)
        if not user:
            return response.json({
                'code': 0,
                'message': 'User not found [user]'
            }, status=401)

        return await handler(user, br, request, *args, **kwargs)

    return new_handler


def user_to_json(record):
    fields = ['id', 'username', 'discriminator',
              'avatar', 'bot', 'mfa_enabled', 'flags',
              'verified']

    d = {}
    for field in fields:
        d[field] = record[field]

    return d
