from sanic import response
from sanic import Blueprint

from .helpers import auth_route, rawguild_to_json, validate
from .schemas import GUILDADD_SCHEMA
from ..utils import snowflake

bp = Blueprint(__name__)


@bp.route('/api/guilds/<guild_id:int>', methods=['GET'])
@auth_route
async def get_guild(user, bridge, request, guild_id):
    guild = await bridge.get_guild(guild_id)

    # TODO: add user-specific keys.
    guild_json = rawguild_to_json(guild)
    return response.json(guild_json)


@bp.route('/api/guilds', methods=['POST'])
@auth_route
async def create_guild(user, br, request):
    """Create guild"""
    payload = validate(request.json, GUILDADD_SCHEMA)
    payload['region'] = 'local'

    raw_guild = {
        'id': snowflake.get_snowflake(),
        'name': payload['name'],
        'icon': payload.get('icon'),
        'owner_id': user['id'],

        'region': payload['region'],

        'verification_level': payload.get('verification_level', 0),
        'default_message_notifications': payload.get(
            'default_message_notifications', 0),
        'explicit_content_filter': payload.get('explicit_content_filter', 0),
    }

    # create a guild
    await br.pool.execute("""
        insert into guilds (id, name, icon, owner_id, region)
        values ($1, $2, $3, $4, $5)
    """, raw_guild['id'], raw_guild['name'],
                          raw_guild['icon'],
                          user['id'], raw_guild['region'])

    # add the owner as a member of the guild
    await br.pool.execute("""
        insert into members (user_id, guild_id)
        values ($1, $2)
    """, user['id'], raw_guild['id'])

    # TODO: maybe communicate gateway of a guild creation
    # and then dispatch GUILD_CREATE ?
    # like calling bridge.dispatch, or something.

    return response.json(raw_guild)
