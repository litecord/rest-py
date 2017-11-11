import logging
import base64

import itsdangerous

from sanic import response
from sanic import Blueprint

from voluptuous import Schema, REMOVE_EXTRA

from .helpers import route
import utils.password as password

bp = Blueprint(__name__)
log = logging.getLogger(__name__)

useradd_schema = Schema({
    'email': str,
    'password': str,
    'username': str,
}, extra=REMOVE_EXTRA)

login_schema = Schema({
    'email': str,
    'password': str,
}, extra=REMOVE_EXTRA)


@bp.route('/api/auth/users/add', methods=['POST'])
@route
async def add_user(br, request):
    payload = useradd_schema(request.json)
    user = await br.get_user_by_email(payload['email'])
    if user:
        raise Exception('User already created')

    rows = await br.create_user(payload)
    if rows > 0:
        return response.json({
            'code': 1,
            'message': 'success',
        })
    else:
        return response.json({
            'code': 0,
            'message': 'no rows were affected',
        })


@bp.route('/api/auth/login', methods=['POST'])
@route
async def login(br, request):
    payload = login_schema(request.json)

    log.info('Trying to authenticate %r', payload['email'])
    user = await br.get_user_by_email(payload['email'])
    if not user:
        raise Exception('User not found')

    salt = user['password_salt']
    if password.pwd_hash(payload['password'], salt) != user['password_hash']:
        raise Exception('Incorrect password')

    s = itsdangerous.TimestampSigner(salt)
    uid_encoded = base64.urlsafe_b64encode(user['id'].encode())
    token = s.sign(uid_encoded).decode()
    log.info('Generated token %s', token)

    return response.json({
        'token': token
    })
