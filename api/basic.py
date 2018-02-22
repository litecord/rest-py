from sanic import response
from sanic import Blueprint

import lconfig

from .helpers import auth_route

bp = Blueprint(__name__)


@bp.route('/api/gateway')
async def get_gateway(request):
    return response.json({
        'url': lconfig.gateway_url,
    })


@bp.get('/api/gateway/bot')
@auth_route
async def get_gateway_bot(user, br, request):
    guild_count = await br.pool.fetchval("""
        select count(*) from members
        where user_id = $1
    """, user.id)

    # allocate guilds per shard
    guilds_per_shard = lconfig.GUILDS_SHARD
    shard_count = max(int(guild_count / guilds_per_shard), 1)

    return response.json({
        'gateway': lconfig.gateway_url,
        'shards': shard_count
    })
