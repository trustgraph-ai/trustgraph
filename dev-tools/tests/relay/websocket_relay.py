#!/usr/bin/env python3
"""
WebSocket Relay Test Harness

This script creates a relay server with two WebSocket endpoints:
- /in  - for test clients to connect to
- /out - for reverse gateway to connect to

Messages are bidirectionally relayed between the two connections.

Usage:
    python websocket_relay.py [--port PORT] [--host HOST]
"""

import asyncio
import logging
import argparse
from aiohttp import web, WSMsgType
import weakref
from typing import Optional, Set

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("websocket_relay")

class WebSocketRelay:
    """WebSocket relay that forwards messages between 'in' and 'out' connections"""
    
    def __init__(self):
        self.in_connections: Set = weakref.WeakSet()
        self.out_connections: Set = weakref.WeakSet()
        
    async def handle_in_connection(self, request):
        """Handle incoming connections on /in endpoint"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.in_connections.add(ws)
        logger.info(f"New 'in' connection. Total in: {len(self.in_connections)}, out: {len(self.out_connections)}")
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    data = msg.data
                    logger.info(f"IN → OUT: {data}")
                    await self._forward_to_out(data)
                elif msg.type == WSMsgType.BINARY:
                    data = msg.data
                    logger.info(f"IN → OUT: {len(data)} bytes (binary)")
                    await self._forward_to_out(data, binary=True)
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"WebSocket error on 'in' connection: {ws.exception()}")
                    break
                else:
                    break
        except Exception as e:
            logger.error(f"Error in 'in' connection handler: {e}")
        finally:
            logger.info(f"'in' connection closed. Remaining in: {len(self.in_connections)}, out: {len(self.out_connections)}")
            
        return ws
    
    async def handle_out_connection(self, request):
        """Handle outgoing connections on /out endpoint"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.out_connections.add(ws)
        logger.info(f"New 'out' connection. Total in: {len(self.in_connections)}, out: {len(self.out_connections)}")
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    data = msg.data
                    logger.info(f"OUT → IN: {data}")
                    await self._forward_to_in(data)
                elif msg.type == WSMsgType.BINARY:
                    data = msg.data
                    logger.info(f"OUT → IN: {len(data)} bytes (binary)")
                    await self._forward_to_in(data, binary=True)
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"WebSocket error on 'out' connection: {ws.exception()}")
                    break
                else:
                    break
        except Exception as e:
            logger.error(f"Error in 'out' connection handler: {e}")
        finally:
            logger.info(f"'out' connection closed. Remaining in: {len(self.in_connections)}, out: {len(self.out_connections)}")
            
        return ws
    
    async def _forward_to_out(self, data, binary=False):
        """Forward message from 'in' to all 'out' connections"""
        if not self.out_connections:
            logger.warning("No 'out' connections available to forward message")
            return
            
        closed_connections = []
        for ws in list(self.out_connections):
            try:
                if ws.closed:
                    closed_connections.append(ws)
                    continue
                    
                if binary:
                    await ws.send_bytes(data)
                else:
                    await ws.send_str(data)
            except Exception as e:
                logger.error(f"Error forwarding to 'out' connection: {e}")
                closed_connections.append(ws)
        
        # Clean up closed connections
        for ws in closed_connections:
            if ws in self.out_connections:
                self.out_connections.discard(ws)
    
    async def _forward_to_in(self, data, binary=False):
        """Forward message from 'out' to all 'in' connections"""
        if not self.in_connections:
            logger.warning("No 'in' connections available to forward message")
            return
            
        closed_connections = []
        for ws in list(self.in_connections):
            try:
                if ws.closed:
                    closed_connections.append(ws)
                    continue
                    
                if binary:
                    await ws.send_bytes(data)
                else:
                    await ws.send_str(data)
            except Exception as e:
                logger.error(f"Error forwarding to 'in' connection: {e}")
                closed_connections.append(ws)
        
        # Clean up closed connections
        for ws in closed_connections:
            if ws in self.in_connections:
                self.in_connections.discard(ws)

async def create_app(relay):
    """Create the web application with routes"""
    app = web.Application()
    
    # Add routes
    app.router.add_get('/in', relay.handle_in_connection)
    app.router.add_get('/out', relay.handle_out_connection)
    
    # Add a simple status endpoint
    async def status(request):
        status_info = {
            'in_connections': len(relay.in_connections),
            'out_connections': len(relay.out_connections),
            'status': 'running'
        }
        return web.json_response(status_info)
    
    app.router.add_get('/status', status)
    app.router.add_get('/', status)  # Root also shows status
    
    return app

def main():
    parser = argparse.ArgumentParser(
        description="WebSocket Relay Test Harness"
    )
    parser.add_argument(
        '--host', 
        default='localhost',
        help='Host to bind to (default: localhost)'
    )
    parser.add_argument(
        '--port', 
        type=int, 
        default=8080,
        help='Port to bind to (default: 8080)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    relay = WebSocketRelay()
    
    print(f"Starting WebSocket Relay on {args.host}:{args.port}")
    print(f"  'in' endpoint:  ws://{args.host}:{args.port}/in")
    print(f"  'out' endpoint: ws://{args.host}:{args.port}/out")
    print(f"  Status:         http://{args.host}:{args.port}/status")
    print()
    print("Usage:")
    print(f"  Test client connects to:     ws://{args.host}:{args.port}/in")
    print(f"  Reverse gateway connects to: ws://{args.host}:{args.port}/out")
    
    web.run_app(create_app(relay), host=args.host, port=args.port)

if __name__ == "__main__":
    main()