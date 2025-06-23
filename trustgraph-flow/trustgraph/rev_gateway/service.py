import asyncio
import logging
import json
import sys
import os
from aiohttp import ClientSession, WSMsgType, ClientWebSocketResponse
from typing import Optional
import pulsar

from .dispatcher import MessageDispatcher
from ..gateway.config.receiver import ConfigReceiver

logger = logging.getLogger("rev_gateway")
logger.setLevel(logging.INFO)

class ReverseGateway:
    
    def __init__(self, host: str = "api.trustgraph.ai", max_workers: int = 10, 
                 pulsar_host: str = None, pulsar_api_key: str = None, 
                 pulsar_listener: str = None):
        self.host = host
        self.url = f"wss://{host}/ws"
        self.max_workers = max_workers
        self.ws: Optional[ClientWebSocketResponse] = None
        self.session: Optional[ClientSession] = None
        self.dispatcher = MessageDispatcher(max_workers)
        self.running = False
        self.reconnect_delay = 3.0
        
        # Pulsar configuration
        self.pulsar_host = pulsar_host or os.getenv("PULSAR_HOST", "pulsar://pulsar:6650")
        self.pulsar_api_key = pulsar_api_key or os.getenv("PULSAR_API_KEY", None)
        self.pulsar_listener = pulsar_listener
        
        # Initialize Pulsar client
        if self.pulsar_api_key:
            self.pulsar_client = pulsar.Client(
                self.pulsar_host, 
                listener_name=self.pulsar_listener,
                authentication=pulsar.AuthenticationToken(self.pulsar_api_key)
            )
        else:
            self.pulsar_client = pulsar.Client(
                self.pulsar_host,
                listener_name=self.pulsar_listener
            )
        
        # Initialize config receiver
        self.config_receiver = ConfigReceiver(self.pulsar_client)
        
    async def connect(self) -> bool:
        try:
            if self.session is None:
                self.session = ClientSession()
                
            logger.info(f"Connecting to {self.url}")
            self.ws = await self.session.ws_connect(self.url)
            logger.info("WebSocket connection established")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
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
            print(f"Received: {message}", flush=True)
            
            msg_data = json.loads(message)
            response = await self.dispatcher.handle_message(msg_data)
            
            if response:
                await self.send_message(response)
                
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
        
        # Start config receiver
        logger.info("Starting config receiver")
        await self.config_receiver.start()
        
        while self.running:
            try:
                if await self.connect():
                    await self.listen()
                else:
                    logger.warning(f"Connection failed, retrying in {self.reconnect_delay} seconds")
                
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
        
        # Close Pulsar client
        if hasattr(self, 'pulsar_client'):
            self.pulsar_client.close()
    
    def stop(self):
        self.running = False