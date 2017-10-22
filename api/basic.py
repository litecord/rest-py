from sanic import response
from sanic import Blueprint

import lconfig

bp = Blueprint(__name__)


@bp.route('/api/gateway')
async def get_gateway(request):
    return response.json({
        'url': lconfig.gateway_url,
    })
