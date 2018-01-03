from sanic import response
from sanic import Blueprint

from .helpers import auth_route, rawguild_to_json

bp = Blueprint(__name__)


@bp.route('/api/guilds/<guild_id:int>', methods=['GET'])
@auth_route
async def get_guild(user, bridge, request, guild_id):
    guild = await bridge.get_guild(guild_id)
    guild_json = rawguild_to_json(guild)
    return response.json(guild_json)


@bp.route('/api/guilds', methods=['POST'])
@auth_route
async def create_guild(user, bridge, request):
    pass
