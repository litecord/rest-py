import logging
import base64

import itsdangerous

from sanic import response
from sanic import Blueprint

import utils.password as password
from .schemas import USERADD_SCHEMA, LOGIN_SCHEMA
from .helpers import route, validate
from .errors import Unauthorized

bp = Blueprint(__name__)
log = logging.getLogger(__name__)

def check_password(user, given_password: str):
    """Check if a password is correct."""
    salt = user['password_salt']
    if password.pwd_hash(given_password, salt) != user['password_hash']:
        raise Unauthorized('Incorrect password')


@bp.route('/api/auth/users/add', methods=['POST'])
@route
async def add_user(br, request):
    """Create one user on the service."""
    validate(request.json, USERADD_SCHEMA)
    payload = request.json

    user = await br.get_user_by_email(payload['email'])
    if user:
        raise Exception('User already created')

    rows = await br.create_user(payload)
    if rows > 0:
        return response.json({
            'code': 1,
            'message': 'success',
        })

    return response.json({
        'code': 0,
        'message': 'no rows were affected',
    })


@bp.route('/api/auth/login', methods=['POST'])
@route
async def login(br, request):
    """Login one user into the service.

    Returns a valid token tied to that user.
    """
    validate(request.json, LOGIN_SCHEMA)
    payload = request.json

    log.info('Trying to authenticate %r', payload['email'])
    user = await br.get_user_by_email(payload['email'])
    if not user:
        raise Exception('User not found')

    salt = user['password_salt']
    check_password(user, payload.get('password'))

    s = itsdangerous.TimestampSigner(salt)
    uid_encoded = base64.urlsafe_b64encode(user['id'].encode())
    token = s.sign(uid_encoded).decode()
    log.info('Generated token %s', token)

    return response.json({
        'token': token
    })
