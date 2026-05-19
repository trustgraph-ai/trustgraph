#!/usr/bin/env python3
"""
WebSocket Relay Test Harness

This script creates a relay server with two WebSocket endpoints:
- /in  - for test clients to connect to (speaks api-gateway protocol)
- /out - for reverse gateway to connect to (speaks rev-gateway protocol)

Clients on /in authenticate with a first-frame auth message:
    {"type": "auth", "token": "..."}

The relay stores the token and injects it into each subsequent message
before forwarding to /out.  Responses from /out are forwarded back to
the originating /in connection unchanged.

Usage:
    python websocket_relay.py [--port PORT] [--host HOST]
"""

import asyncio
import json
import logging
import argparse
from aiohttp import web, WSMsgType
from typing import Dict, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("websocket_relay")


class InConnection:
    def __init__(self, ws, conn_id):
        self.ws = ws
        self.conn_id = conn_id
        self.token: Optional[str] = None
        self.authenticated = False


class WebSocketRelay:

    def __init__(self):
        self.in_connections: Dict[str, InConnection] = {}
        self.out_connections: set = set()
        self._conn_counter = 0

    def _next_conn_id(self):
        self._conn_counter += 1
        return f"conn-{self._conn_counter}"

    async def handle_in_connection(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        conn_id = self._next_conn_id()
        conn = InConnection(ws, conn_id)
        self.in_connections[conn_id] = conn
        logger.info(
            f"New 'in' connection {conn_id}. "
            f"Total in: {len(self.in_connections)}, "
            f"out: {len(self.out_connections)}"
        )

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    await self._handle_in_message(conn, msg.data)
                elif msg.type == WSMsgType.ERROR:
                    logger.error(
                        f"WebSocket error on 'in' connection "
                        f"{conn_id}: {ws.exception()}"
                    )
                    break
                else:
                    break
        except Exception as e:
            logger.error(
                f"Error in 'in' connection {conn_id}: {e}"
            )
        finally:
            del self.in_connections[conn_id]
            logger.info(
                f"'in' connection {conn_id} closed. "
                f"Remaining in: {len(self.in_connections)}, "
                f"out: {len(self.out_connections)}"
            )

        return ws

    async def _handle_in_message(self, conn, data):
        try:
            message = json.loads(data)
        except json.JSONDecodeError:
            logger.warning(
                f"{conn.conn_id}: received non-JSON message"
            )
            return

        if isinstance(message, dict) and message.get("type") == "auth":
            conn.token = message.get("token", "")
            conn.authenticated = True
            logger.info(f"{conn.conn_id}: authenticated")
            await conn.ws.send_json({
                "type": "auth-ok",
                "workspace": "relayed",
            })
            return

        if not conn.authenticated:
            await conn.ws.send_json({
                "error": {
                    "message": "auth required",
                    "type": "auth-required",
                },
                "complete": True,
            })
            return

        message["token"] = conn.token
        message["_relay_conn"] = conn.conn_id

        forwarded = json.dumps(message)
        logger.info(f"IN {conn.conn_id} → OUT: {forwarded}")
        await self._forward_to_out(forwarded)

    async def handle_out_connection(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        self.out_connections.add(ws)
        logger.info(
            f"New 'out' connection. "
            f"Total in: {len(self.in_connections)}, "
            f"out: {len(self.out_connections)}"
        )

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    await self._handle_out_message(msg.data)
                elif msg.type == WSMsgType.ERROR:
                    logger.error(
                        f"WebSocket error on 'out' connection: "
                        f"{ws.exception()}"
                    )
                    break
                else:
                    break
        except Exception as e:
            logger.error(f"Error in 'out' connection: {e}")
        finally:
            self.out_connections.discard(ws)
            logger.info(
                f"'out' connection closed. "
                f"Remaining in: {len(self.in_connections)}, "
                f"out: {len(self.out_connections)}"
            )

        return ws

    async def _handle_out_message(self, data):
        try:
            message = json.loads(data)
        except json.JSONDecodeError:
            logger.warning("OUT: received non-JSON message")
            return

        conn_id = message.pop("_relay_conn", None)

        forwarded = json.dumps(message)
        logger.info(f"OUT → IN {conn_id or 'broadcast'}: {forwarded}")

        if conn_id and conn_id in self.in_connections:
            conn = self.in_connections[conn_id]
            try:
                if not conn.ws.closed:
                    await conn.ws.send_str(forwarded)
            except Exception as e:
                logger.error(
                    f"Error forwarding to 'in' {conn_id}: {e}"
                )
        else:
            await self._broadcast_to_in(forwarded)

    async def _broadcast_to_in(self, data):
        closed = []
        for conn_id, conn in list(self.in_connections.items()):
            try:
                if conn.ws.closed:
                    closed.append(conn_id)
                    continue
                await conn.ws.send_str(data)
            except Exception as e:
                logger.error(
                    f"Error broadcasting to 'in' {conn_id}: {e}"
                )
                closed.append(conn_id)
        for conn_id in closed:
            self.in_connections.pop(conn_id, None)

    async def _forward_to_out(self, data):
        closed = []
        for ws in list(self.out_connections):
            try:
                if ws.closed:
                    closed.append(ws)
                    continue
                await ws.send_str(data)
            except Exception as e:
                logger.error(f"Error forwarding to 'out': {e}")
                closed.append(ws)
        for ws in closed:
            self.out_connections.discard(ws)


async def create_app(relay):
    app = web.Application()

    app.router.add_get('/in/api/v1/socket', relay.handle_in_connection)
    app.router.add_get('/out', relay.handle_out_connection)

    async def status(request):
        return web.json_response({
            'in_connections': len(relay.in_connections),
            'out_connections': len(relay.out_connections),
            'status': 'running',
        })

    app.router.add_get('/status', status)
    app.router.add_get('/', status)

    return app


def main():
    parser = argparse.ArgumentParser(
        description="WebSocket Relay Test Harness"
    )
    parser.add_argument(
        '--host',
        default='localhost',
        help='Host to bind to (default: localhost)',
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8080,
        help='Port to bind to (default: 8080)',
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging',
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    relay = WebSocketRelay()

    print(f"Starting WebSocket Relay on {args.host}:{args.port}")
    print(f"  'in' endpoint:  ws://{args.host}:{args.port}/in/api/v1/socket")
    print(f"  'out' endpoint: ws://{args.host}:{args.port}/out")
    print(f"  Status:         http://{args.host}:{args.port}/status")
    print()
    print("Client protocol (same as api-gateway):")
    print('  1. Connect to /in/api/v1/socket')
    print('  2. Send: {"type": "auth", "token": "tg_..."}')
    print('  3. Receive: {"type": "auth-ok", "workspace": "relayed"}')
    print('  4. Send requests as normal')

    web.run_app(create_app(relay), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
