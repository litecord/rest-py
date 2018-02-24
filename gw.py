import logging
import collections
import json
import asyncio
import os
import hashlib
import random
import base64

import itsdangerous
import asyncpg
import websockets

import lconfig
import utils.snowflake as snowflake
import utils.password as password

log = logging.getLogger(__name__)


class OP:
    """Litebridge OP codes."""
    hello = 0
    hello_ack = 1
    heartbeat = 2
    heartbeat_ack = 3
    request = 4
    response = 5
    dispatch = 6


def random_nonce() -> str:
    """Generate a random nonce for requests."""
    return hashlib.md5(os.urandom(128)).hexdigest()


class Connection:
    """Litebridge connection class."""
    def __init__(self, bridge):
        self.br = bridge
        self.ws = None
        self.good_state = False

        self._hb_good = True
        self._hb_seq = 0

        self.loop_task = None
        self.hb_task = None
        self._retries = 0
        self._requests = collections.defaultdict(asyncio.Event)

    async def recv(self):
        """Receive one message from the websocket."""
        return json.loads(await self.ws.recv())

    async def send(self, obj):
        """Send a message to the websocket."""
        await self.ws.send(json.dumps(obj))

    async def heartbeat(self, hello: dict):
        """Heartbeat with the server."""
        try:
            period = hello['hb_interval'] / 1000
            period = round(period, 5)
            log.info(f'Heartbeating period is {period} seconds')
            while True:
                if not self._hb_good:
                    log.warning('We did not receive an ACK from the server.')
                    self.good_state = False

                    # Clean everything and restart:
                    # better try to restart
                    # then see everything crash on fire
                    self.loop_task.close()
                    await self.ws.close()
                    await self.init()
                    return

                log.debug('Heartbeating with the gateway')
                await self.send({
                    'op': OP.heartbeat,
                    's': self._hb_seq,
                })
                self._hb_good = False

                await asyncio.sleep(period)
        except asyncio.CancelledError:
            log.warning('Heartbeat task cancelled.')
        except websockets.exceptions.ConnectionClosed as err:
            log.error(f'Connection failed. {err!r}')

        self.good_state = False

    async def loop(self):
        """Enter an infinite loop receiving packets."""
        try:
            while True:
                payload = await self.recv()
                opcode = payload['op']

                log.debug('Handling OP %d', opcode)
                if opcode == OP.heartbeat_ack:
                    log.debug("Gateway ACK'd our heartbeat")
                    self._hb_good = True
                    self._hb_seq += 1
                else:
                    await self.dispatch_packet(opcode, payload)
        except websockets.ConnectionClosed:
            log.info('Closed, trying to reconnect...')

            await self.ws.close()
            await self.init()
        except Exception:
            log.exception('Error in main receive loop')

    async def dispatch_packet(self, opcode: int, payload: dict):
        """Handle a packet sent by the client.
        """
        if opcode == OP.request:
            # Server requested something from us
            rtype = payload['w']
            rargs = payload['a']
            nonce = payload['n']
            handler = getattr(self, f'req_{rtype.lower()}', None)
            if handler:
                result = await handler(nonce, *rargs)
                await self.send({
                    'op': OP.response,
                    'r': result,
                    'n': nonce
                })
            else:
                log.warning('Unknown request: %s', rtype)

        elif opcode == OP.dispatch:
            # Server requested something from us (a dispatch)
            pass
        elif opcode == OP.response:
            # We requested something, server's
            # responding
            pass
        else:
            log.warning('Unknown OP code: %d', opcode)

    async def req_token_validate(self, nonce: int, token: str):
        """Token validation handler."""
        status, err = await self.br.token_valid(token)
        if status:
            return True
        return False, err

    async def dispatch(self, name: str, args):
        """Dispatch something to the server.

        We will not get any response back.
        """
        await self.send({
            'op': OP.dispatch,
            'w': name,
            'a': args,
        })

    async def request(self, name, args, **kwargs):
        """Request something from the server.

        This will block the calling coroutine until
        a response is given.

        Optionally, you can add a timeout as a keyword argument.
        """
        # TODO: implementation
        pass

    async def ws_init(self):
        """Initialize the websocket
        connection with the litebridge server.
        """
        hello = await self.recv()
        if hello['op'] != OP.hello:
            raise RuntimeError('Received HELLO is not HELLO')

        log.debug('Authenticating')
        await self.send({
            'op': OP.hello_ack,
            'password': lconfig.litebridge_password,
        })

        log.debug('firing tasks')
        self.loop_task = self.br.loop.create_task(self.loop())
        self.hb_task = self.br.loop.create_task(self.heartbeat(hello))

    def cleanup(self):
        """Destroy any websocket-processing tasks."""
        if self.loop_task:
            self.loop_task.cancel()
            self.loop_task = None

        if self.hb_task:
            self.hb_task.cancel()
            self.hb_task = None

    async def init(self):
        """Connect to the bridge websocket and start
        the processing tasks."""
        try:
            self.cleanup()
            self._retries += 1

            log.info('Connecting to the gateway [try: %d]...', self._retries)
            self.ws = await websockets.connect(lconfig.litebridge_server)
            await self.ws_init()
        except Exception as err:
            retry = random.uniform(1, 8)
            log.error('Error while connecting, retrying in'
                      f' {retry:.2} seconds: {err!r}')
            await asyncio.sleep(retry)

            # recursion am i right
            await self.init()


class Bridge:
    def __init__(self, app, server, loop):
        self.server = server
        self.loop = loop

        self.ws = None
        self.pool = None
        self.app = app

        # aliases to this instance
        app.bridge = self

    async def init(self):
        """Connect to database and instantiate a websocket connection."""
        self.pool = await asyncpg.create_pool(**lconfig.pgargs)
        self.ws = Connection(self)

        self.loop.create_task(self.server)
        self.loop.create_task(self.ws.init())

    async def token_valid(self, token: str) -> tuple:
        """Check if a token is valid."""
        encoded_uid, _, _ = token.split('.')
        uid = base64.urlsafe_b64decode(encoded_uid).decode('utf-8')

        log.debug('uid: %r', uid)

        user = await self.get_user(uid)
        if not user:
            return False, 'user not found'

        salt = user['password_salt']
        signer = itsdangerous.TimestampSigner(salt)
        try:
            signer.unsign(token)
            return True, uid
        except itsdangerous.BadSignature:
            return False, 'bad token'

    async def get_user(self, user_id) -> asyncpg.Record:
        """Get one user in the service."""
        user = await self.pool.fetchrow("""
        SELECT * FROM users
        WHERE id=$1
        """, user_id)

        log.info('[user:by_id] %s -> %r', user_id, user)
        return user

    async def get_user_by_email(self, email: str) -> dict:
        """Get one user by its email in the service."""
        user = await self.pool.fetchrow("""
        SELECT * FROM users
        WHERE email=$1
        """, email)

        log.info('[user:by_email] %s -> %r', email, user)
        return user

    async def generate_discrim(self, username: str) -> str:
        """Generate a discriminator based on a username."""
        # First, get amount of users

        discrims = await self.pool.fetch("""
        SELECT (discriminator) FROM users WHERE username = $1;
        """, username)

        print(discrims)
        if len(discrims) >= 9999:
            # Dropping it because we already have too much
            raise Exception('Too many users have this username')

        # Check if random discrim is already used
        # and if it is already used, generate another one
        # TODO: use SQL for this ??
        rdiscrim = await password.random_digits(4)

        while rdiscrim in discrims:
            rdiscrim = await password.random_digits(4)

        log.info('Generated discrim %s for %r',
                 rdiscrim, username)

        return rdiscrim

    async def create_user(self, payload: dict):
        """Create one user, given a user payload."""
        # create a snowflake
        user_id = snowflake.get_snowflake()
        log.info('Generated snowflake %d', user_id)

        discrim = await self.generate_discrim(payload['username'])

        # generate passwords
        salt = password.get_random_salt()
        pwd_hash = password.pwd_hash(payload['password'],
                                     salt)

        res = await self.pool.execute("""
        INSERT INTO users (id, username, discriminator,
        email, password_salt, password_hash)

        VALUES ($1, $2, $3, $4, $5, $6)
        """, str(user_id), payload['username'], discrim,
                                      payload['email'], salt, pwd_hash)

        _, _, rows = res.split()
        return int(rows)
