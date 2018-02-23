from sanic import response
from sanic import Blueprint

from .helpers import auth_route, user_to_json, validate
from .errors import ApiError, Unauthorized, UnknownUser
from .schemas import USERMOD_SCHEMA


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
    """Modify current user."""
    payload = validate(request.json, USERMOD_SCHEMA)
    result_user = dict(user)

    new_username = payload.get('username')
    if new_username and new_username != user['username']:
        # proceed for a new discrim
        new_discrim = br.generate_discrim(new_username)

        await br.pool.execute("""
            update users
            set discriminator=$1, username=$2
            where id=$3
        """, new_discrim, new_username, user['id'])

        result_user['discriminator'] = new_discrim
        result_user['username'] = new_username

    new_avatar = payload.get('avatar')
    if new_avatar:
        await br.pool.execute("""
            update users
            set avatar=$1
            where id=$2
        """, new_avatar, user['id'])

        result_user['avatar'] = new_avatar

    new_email = payload.get('email')
    if new_email and new_email != user['email']:
        # TODO: check password
        result_user['email'] = new_email

    return user_to_json(user)


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
