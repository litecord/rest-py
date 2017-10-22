from sanic import response
from sanic import Blueprint

# import db
# will give stuff like get_user and get_guild

# import gw
# will enable us to communicate with gateway

from .helpers import auth_route


bp = Blueprint(__name__)


# auth_route decorator
#  Will check Authorization header
#  Will also give the request handler
#   a User object and a Bridge object

@bp.route('/api/users/@me')
@auth_route
async def get_me(user, br, request):
    return response.json(user.json)


@bp.route('/api/users/<user_id:int>')
@auth_route
async def get_user(user, br, request, user_id):
    if user.bot:
        return response.text('Unauthorized', status=401)

    other = await br.get_user(user_id)
    if not other:
        return response.text('User not found', status=404)

    return response.json(other.json)


@bp.route('/api/users/@me', methods=['POST'])
@auth_route
async def patch_me(user, br, request):
    pass


@bp.route('/api/users/@me/guilds')
@auth_route
async def get_me_guilds(user, br, request):
    # TODO: query string parameters
    guild_list = await br.get_guilds(user.id)
    return response.json([g.json for g in guild_list])


@bp.route('/api/users/@me/guilds/<guild_id:int>', methods=['DELETE'])
@auth_route
async def leave_guild(user, br, request, guild_id):
    guild = await br.get_user_guild(user.id, guild_id)
    if not guild:
        return response.text('Guild not found', status=404)

    try:
        await br.pop_member(guild, user)
    except br.MemberError as err:
        return response.text(f'Error removing: {err!r}', status=500)

    return response.text('', status=204)
