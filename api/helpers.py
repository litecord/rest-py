import logging

from sanic import response
from sanic.exceptions import ServerError

from .schemas import v
from .errors import LitecordValidationError

log = logging.getLogger(__name__)


def validate(document: dict, schema: dict) -> dict:
    """Validate one document against the schema provided.

    Parameters
    ----------
    document: dict
        The original document to be validated.
    schema: dict
        The schema that this document will be validated against.

    Returns
    -------
    dict
        The original document.

        Might be a normalized version of it in later iterations.

    Raises
    ------
    LitecordValidationError
        On any payload error.
    """
    res = v.validate(document, schema)
    if not res:
        raise LitecordValidationError('Bad payload', v.errors)

    return document


def get_token(request) -> str:
    """Get a token from a request object."""
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
    """Check if a request has a valid token."""
    token = get_token(request)
    if not token:
        raise ServerError('Authorization not provided', status_code=401)

    # TODO: check token here
    log.info('token: %s', token)
    pass


def route(handler):
    async def new_handler(request, *args, **kwargs):
        bridge = request.app.bridge
        return await handler(bridge, request, *args, **kwargs)

    return new_handler


def auth_route(handler):
    """Generate an authentication-only route."""
    async def new_handler(request, *args, **kwargs):
        """Request handler."""
        bridge = request.app.bridge
        token = get_token(request)
        log.info('token: %s', token)

        if not token:
            return response.json({
                'code': 0,
                'message': '401: Unauthorized'
            }, status=401)

        succ, user_id = await bridge.token_valid(token)
        if not succ:
            return response.json({
                'code': 0,
                'message': 'User not found [id]'
            }, status=401)

        user = await bridge.get_user(user_id)
        if not user:
            return response.json({
                'code': 0,
                'message': 'User not found [user]'
            }, status=401)

        return await handler(user, bridge, request, *args, **kwargs)

    return new_handler


def to_json(record, fields) -> dict:
    """Convert a record with its fields to a dictionary."""
    dct = {}
    for field in fields:
        dct[field] = record[field]

    return dct


def user_to_json(record) -> dict:
    """Convert a raw user record to JSON."""
    fields = ['id', 'username', 'discriminator',
              'avatar', 'bot', 'mfa_enabled', 'flags',
              'verified']
    return to_json(record, fields)


def rawguild_to_json(record) -> dict:
    """Convert a raw guild record to JSON.

    If you want to send a full guild object
    to the user, you will have to combine
    the data from here with more information
    like roles, members, etc.
    """
    fields = ['id', 'name', 'owner_id', 'region',
              'afk_channel_id', 'afk_timeout',
              'embed_enabled', 'verification_level',
              'default_message_notifications',
              'explicit_content_fileter',
              'mfa_level', 'widget_enabled',
              'widget_channel_id', 'system_channel_id']
    return to_json(record, fields)
