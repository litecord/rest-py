
from sanic import response
from sanic.exceptions import ServerError


def get_token(request):
    prefixes = ('Bearer', 'Bot')
    raw = request.headers.get('Authorization')
    if not raw:
        return

    for prefix in prefixes:
        if raw.startswith(prefix):
            return raw.replace(prefix, '').strip()


async def authorize(request):
    token = get_token(request)
    if not token:
        raise ServerError('Authorization not provided', status_code=401)

    # check token here
    pass


def auth_route(handler):
    async def new_handler(request, *args):
        br = request.app.bridge
        token = get_token(request)
        if not token:
            return response.json({
                'code': 0,
                'message': '401: Unauthorized'
            }, status=401)

        user_id = br.token_valid(token)
        if not user_id:
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

        return await handler(user, br, request, *args)

    return new_handler
