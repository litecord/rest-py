from sanic import response
from sanic import Blueprint

from .helpers import auth_route, user_to_json
from .errors import ApiError, Unauthorized, UnknownUser


bp = Blueprint(__name__)


@bp.route('/api/users/@me')
@auth_route
async def get_me(user, br, request):
    """Get the current user."""
    return response.json(user_to_json(user))


@bp.route('/api/users/<user_id:int>')
@auth_route
async def get_user(user, br, request, user_id):
    """Get any user."""
    if user.bot:
        raise Unauthorized('Users can not use this endpoint')

    other = await br.get_user(user_id)
    if not other:
        raise UnknownUser('User not found')

    return response.json(other.json)


@bp.patch('/api/users/@me')
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
        raise ApiError(f'error removing user: {err!r}')

    return response.text('', status=204)
