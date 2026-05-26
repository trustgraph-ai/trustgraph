"""
Reverse gateway.  Initiates outbound WebSocket connections to a remote
relay and dispatches incoming requests through the same DispatcherManager
pipeline as api-gateway.
"""

import asyncio
import argparse
import logging
import json
import sys
import os
from aiohttp import ClientSession, WSMsgType, ClientWebSocketResponse
from typing import Optional
from urllib.parse import urlparse, urlunparse

from .dispatcher import MessageDispatcher
from ..gateway.auth import IamAuth
from ..gateway.config.receiver import ConfigReceiver
from ..base.pubsub import get_pubsub, add_pubsub_args
from ..base.logging import setup_logging, add_logging_args

logger = logging.getLogger("rev_gateway")

default_websocket = "ws://localhost:7650/out"
default_timeout = 600

class ReverseGateway:

    def __init__(self, **config):
        websocket_uri = config.get("websocket_uri")
        if websocket_uri is None:
            websocket_uri = os.getenv("WEBSOCKET_URI", default_websocket)

        parsed_uri = urlparse(websocket_uri)
        if parsed_uri.scheme not in ('ws', 'wss'):
            raise ValueError(
                f"WebSocket URI must use ws:// or wss:// scheme, "
                f"got: {parsed_uri.scheme}"
            )
        if not parsed_uri.netloc:
            raise ValueError(
                f"WebSocket URI must include hostname, "
                f"got: {websocket_uri}"
            )

        self.websocket_uri = websocket_uri
        self.host = parsed_uri.hostname
        self.port = parsed_uri.port
        self.scheme = parsed_uri.scheme
        self.path = parsed_uri.path or "/ws"

        if not parsed_uri.path:
            self.url = f"{self.scheme}://{parsed_uri.netloc}/ws"
        else:
            self.url = websocket_uri

        self.max_workers = int(config.get("max_workers", 10))
        self.timeout = int(config.get("timeout", default_timeout))
        self.ws: Optional[ClientWebSocketResponse] = None
        self.session: Optional[ClientSession] = None
        self.running = False
        self.reconnect_delay = 3.0

        self.backend = get_pubsub(**config)

        self.auth = IamAuth(
            backend=self.backend,
            id=config.get("id", "rev-gateway"),
        )

        self.config_receiver = ConfigReceiver(
            self.backend, auth=self.auth,
        )

        self.dispatcher = MessageDispatcher(
            self.max_workers, self.config_receiver, self.backend,
            auth=self.auth, timeout=self.timeout,
        )

    async def connect(self) -> bool:
        try:
            if self.session is None:
                self.session = ClientSession()

            logger.info(f"Connecting to {self.url}")
            self.ws = await self.session.ws_connect(self.url)
            logger.info(
                f"WebSocket connection established to "
                f"{self.host}:{self.port or 'default'}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to connect to {self.url}: {e}")
            return False

    async def disconnect(self):
        if self.ws and not self.ws.closed:
            await self.ws.close()
        if self.session and not self.session.closed:
            await self.session.close()
        self.ws = None
        self.session = None

    async def send_message(self, message: dict):
        if self.ws and not self.ws.closed:
            try:
                await self.ws.send_str(json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to send message: {e}")

    async def handle_message(self, message: str):
        try:
            logger.debug(f"Received message: {message}")

            msg_data = json.loads(message)
            await self.dispatcher.handle_message(
                msg_data, self.send_message,
            )

        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def listen(self):
        while self.running and self.ws and not self.ws.closed:
            try:
                msg = await self.ws.receive()

                if msg.type == WSMsgType.TEXT:
                    await self.handle_message(msg.data)
                elif msg.type == WSMsgType.BINARY:
                    await self.handle_message(msg.data.decode('utf-8'))
                elif msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                    logger.warning("WebSocket closed or error occurred")
                    break

            except Exception as e:
                logger.error(f"Error in listen loop: {e}")
                break

    async def run(self):
        self.running = True
        logger.info("Starting reverse gateway")

        await self.auth.start()
        await self.config_receiver.start()

        while self.running:
            try:
                if await self.connect():
                    await self.listen()
                else:
                    logger.warning(
                        f"Connection failed, retrying in "
                        f"{self.reconnect_delay} seconds"
                    )

                await self.disconnect()

                if self.running:
                    await asyncio.sleep(self.reconnect_delay)

            except KeyboardInterrupt:
                logger.info("Shutdown requested")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                if self.running:
                    await asyncio.sleep(self.reconnect_delay)

        await self.shutdown()

    async def shutdown(self):
        logger.info("Shutting down reverse gateway")
        self.running = False
        await self.dispatcher.shutdown()
        await self.disconnect()

        if hasattr(self, 'backend'):
            self.backend.close()

    def stop(self):
        self.running = False


def run():

    parser = argparse.ArgumentParser(
        prog="reverse-gateway",
        description=__doc__,
    )

    parser.add_argument(
        '--id',
        default='rev-gateway',
        help='Service identifier (default: rev-gateway)',
    )

    parser.add_argument(
        '--websocket-uri',
        default=None,
        help=f'WebSocket URI to connect to (default: {default_websocket})',
    )

    parser.add_argument(
        '--max-workers',
        type=int,
        default=10,
        help='Maximum concurrent message handlers (default: 10)',
    )

    parser.add_argument(
        '--timeout',
        type=int,
        default=default_timeout,
        help=f'Request timeout in seconds (default: {default_timeout})',
    )

    add_pubsub_args(parser)
    add_logging_args(parser)

    args = parser.parse_args()
    args = vars(args)

    setup_logging(args)

    gateway = ReverseGateway(**args)

    logger.info(f"Starting reverse gateway:")
    logger.info(f"  WebSocket URI: {gateway.url}")
    logger.info(f"  Max workers: {gateway.max_workers}")

    try:
        asyncio.run(gateway.run())
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
