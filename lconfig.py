# configuration for litecord rest

# Where to start the webserver
server_url = ('0.0.0.0', 8000)
ssl = False
ssl_certfile = ''
ssl_keyfile = ''

# Where the gateway is in the world
gateway_url = 'ws://localhost:8081/gw'

# Where the litebridge connection will happen
litebridge_server = 'ws://localhost:10101/'
litebridge_password = '123'

# Postgres arguments
pgargs = {
    'user': 'litecord',
    'password': '123',
    'database': 'litecord',
}

# recommended amount is 1000 guilds for each shard
# changing this can lead to overall service degradation
# on high loads
GUILDS_SHARD = 1000
