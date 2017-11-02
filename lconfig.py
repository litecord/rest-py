# configuration for litecord rest

# Where to start the webserver
server_url = ('0.0.0.0', 8000)
ssl = False
ssl_certfile = ''
ssl_keyfile = ''

# Where the gateway is in the world
gateway_url = 'ws://localhost:8080/gw'

# Where the litebridge connection will happen
litebridge_server = 'ws://localhost:8080/bridge'
litebridge_password = '123'
