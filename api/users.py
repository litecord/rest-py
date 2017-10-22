from sanic import response
from sanic import Blueprint

# import db
# will give stuff like get_user and get_guild

# import gw
# will enable us to communicate with gateway

bp = Blueprint(__name__)


@bp.route('/api/users/@me')
async def get_me(request):
    pass


@bp.route('/api/users/<user_id:int>')
async def get_user(request, user_id):
    pass
