import logging
import json
import asyncio
import os
import hashlib
import random
import asyncpg

import websockets

import lconfig

import utils.snowflake as snowflake
import utils.password as password

log = logging.getLogger(__name__)


class OP:
    hello = 0
    hello_ack = 1
    heartbeat = 2
    heartbeat_ack = 3
    request = 4
    response = 5
    dispatch = 6


def random_nonce():
    return hashlib.md5(os.urandom(128)).hexdigest()


class Connection:
    def __init__(self, parent):
        self.parent = parent
        self.ws = None
        self.good_state = False
        self._hb_good = True

        self.loop_task = None
        self.hb_task = None
        self._retries = 0

    async def recv(self):
        return json.loads(await self.ws.recv())

    async def send(self, obj):
        await self.ws.send(json.dumps(obj))

    async def heartbeat(self, hello):
        try:
            period = hello['hb_interval'] / 1000
            log.info('hb: %.2f', period)
            while True:
                if not self._hb_good:
                    log.warning('We did not receive an ACK from the server.')
                    self.good_state = False

                    # Clean everything and restart:
                    # better try to restart
                    # then see everything crash on fire
                    self.loop_task.stop()
                    await self.ws.close()
                    await self.init()
                    return

                log.debug('Heartbeating with the gateway')
                await self.send({
                    'op': OP.heartbeat
                })
                self._hb_good = False

                await asyncio.sleep(period)
        except asyncio.CancelledError:
            log.exception('Cancelled')
            self.good_state = False
            pass

    async def loop(self):
        """Enter an infinite loop receiving packets."""
        try:
            while True:
                payload = await self.recv()
                opcode = payload['op']

                if opcode == OP.heartbeat_ack:
                    log.debug("Gateway ACK'd our heartbeat")
                    self._hb_good = True
                elif opcode == OP.response:
                    pass
                else:
                    log.warning('Unknown OP code %d', opcode)
        except websockets.ConnectionClosed as err:
            log.info('Closed, trying a reconnect...')
            # self.loop_task.stop()
            await self.ws.close()
            await self.init()

            log.info('Finished')
            return
        except:
            log.exception('Error in main receive loop')

    async def ws_init(self):
        hello = await self.recv()
        if hello['op'] != OP.hello:
            raise RuntimeError('Received HELLO is not HELLO')

        log.info('Authenticating')
        await self.send({
            'op': OP.hello_ack,
            'password': lconfig.litebridge_password,
        })

        log.info('firing tasks')
        self.loop_task = self.parent.loop.create_task(self.loop())
        self.hb_task = self.parent.loop.create_task(self.heartbeat(hello))

    async def init(self):
        try:
            self._retries += 1

            if self._retries > 5:
                log.warning('Retried a connection 5 times, too much.')
                return

            log.info('Connecting to the gateway [try: %d]...', self._retries)
            self.ws = await websockets.connect(lconfig.litebridge_server)
            await self.ws_init()
        except:
            sec = random.uniform(1, 10)
            log.exception('Error while connecting, retrying in %.2f seconds',
                          sec)
            await asyncio.sleep(sec)

            # recursion am i right
            await self.init()


class Bridge:
    def __init__(self, app, server, loop):
        self.ws = None
        self.app = app

        # aliases to this instance
        app.bridge = self
        app.br = self

        self.server = server
        self.loop = loop

    async def init(self):
        log.info('Starting rest-py')
        self.ws = Connection(self)
        self.pool = await asyncpg.create_pool(**lconfig.pgargs)

        self.loop.create_task(self.server)
        self.loop.create_task(self.ws.init())
        log.info('Finished.')

    async def get_user(self, user_id):
        user = await self.pool.fetchrow("""
        SELECT * FROM users
        WHERE id=$1
        """, user_id)

        return user

    async def get_user_by_email(self, email: str) -> dict:
        stmt = await self.pool.fetchrow("""
        SELECT * FROM users
        WHERE email=$1
        """, email)

        log.info('[user:by_email] %s -> %r', email, stmt)
        return stmt

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
        # TODO: use SQL for this
        rdiscrim = await password.random_digits(4)

        while rdiscrim in discrims:
            rdiscrim = await password.random_digits(4)

        log.info('Generated discrim %s for %r',
                 rdiscrim, username)

        return rdiscrim

    async def create_user(self, payload):
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
