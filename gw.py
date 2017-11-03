import logging
import json
import asyncio
import os
import hashlib
import random

import websockets

import lconfig

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
            log.info('Connecting to the gateway...')
            self.ws = await websockets.connect(lconfig.litebridge_server)
            log.info('Initializing ws...')
            await self.ws_init()
        except:
            sec = random.uniform(1, 10)
            log.exception('Error while connecting, retrying in %.2f seconds', sec)
            await asyncio.sleep(sec)
            await self.init()


class Bridge:
    def __init__(self, app, server, loop):
        self.ws = None
        self.app = app
        app.bridge = self
        self.server = server
        self.loop = loop

    async def init(self):
        log.info('Starting rest-py')
        self.ws = Connection(self)

        self.loop.create_task(self.server)
        self.loop.create_task(self.ws.init())
        log.info('Finished.')
