#!/usr/bin/env python3
"""
WebSocket Test Client

A simple client to test the reverse gateway through the relay.
Connects to the relay's /in endpoint and allows sending test messages.

Usage:
    python test_client.py [--uri URI] [--interactive]
"""

import asyncio
import json
import logging
import argparse
import uuid
from aiohttp import ClientSession, WSMsgType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_client")

class TestClient:
    """Simple WebSocket test client"""
    
    def __init__(self, uri: str):
        self.uri = uri
        self.session = None
        self.ws = None
        self.running = False
        self.message_counter = 0
        self.client_id = str(uuid.uuid4())[:8]
        
    async def connect(self):
        """Connect to the WebSocket"""
        self.session = ClientSession()
        logger.info(f"Connecting to {self.uri}")
        self.ws = await self.session.ws_connect(self.uri)
        logger.info("Connected successfully")
        
    async def disconnect(self):
        """Disconnect from WebSocket"""
        if self.ws and not self.ws.closed:
            await self.ws.close()
        if self.session and not self.session.closed:
            await self.session.close()
        logger.info("Disconnected")
        
    async def send_message(self, service: str, request_data: dict, flow: str = "default"):
        """Send a properly formatted TrustGraph message"""
        self.message_counter += 1
        message = {
            "id": f"{self.client_id}-{self.message_counter}",
            "service": service,
            "request": request_data,
            "flow": flow
        }
        
        message_json = json.dumps(message, indent=2)
        logger.info(f"Sending message:\n{message_json}")
        await self.ws.send_str(json.dumps(message))
        
    async def listen_for_responses(self):
        """Listen for incoming messages"""
        logger.info("Listening for responses...")
        
        async for msg in self.ws:
            if msg.type == WSMsgType.TEXT:
                try:
                    response = json.loads(msg.data)
                    logger.info(f"Received response:\n{json.dumps(response, indent=2)}")
                except json.JSONDecodeError:
                    logger.info(f"Received text: {msg.data}")
            elif msg.type == WSMsgType.BINARY:
                logger.info(f"Received binary data: {len(msg.data)} bytes")
            elif msg.type == WSMsgType.ERROR:
                logger.error(f"WebSocket error: {self.ws.exception()}")
                break
            else:
                logger.info(f"Connection closed: {msg.type}")
                break
                
    async def interactive_mode(self):
        """Interactive mode for manual testing"""
        print("\n=== Interactive Test Client ===")
        print("Available commands:")
        print("  text-completion - Test text completion service")
        print("  agent          - Test agent service")
        print("  embeddings     - Test embeddings service")
        print("  custom         - Send custom message")
        print("  quit           - Exit")
        print()
        
        # Start response listener
        listen_task = asyncio.create_task(self.listen_for_responses())
        
        try:
            while True:
                try:
                    command = input("Command> ").strip().lower()
                    
                    if command == "quit":
                        break
                    elif command == "text-completion":
                        await self.send_message("text-completion", {
                            "system": "You are a helpful assistant.",
                            "prompt": "What is 2+2?"
                        })
                    elif command == "agent":
                        await self.send_message("agent", {
                            "question": "What is the capital of France?"
                        })
                    elif command == "embeddings":
                        await self.send_message("embeddings", {
                            "text": "Hello world"
                        })
                    elif command == "custom":
                        service = input("Service name> ").strip()
                        request_json = input("Request JSON> ").strip()
                        try:
                            request_data = json.loads(request_json)
                            await self.send_message(service, request_data)
                        except json.JSONDecodeError as e:
                            print(f"Invalid JSON: {e}")
                    elif command == "":
                        continue
                    else:
                        print(f"Unknown command: {command}")
                        
                except KeyboardInterrupt:
                    break
                except EOFError:
                    break
                except Exception as e:
                    logger.error(f"Error in interactive mode: {e}")
                    
        finally:
            listen_task.cancel()
            try:
                await listen_task
            except asyncio.CancelledError:
                pass
            
    async def run_predefined_tests(self):
        """Run a series of predefined tests"""
        print("\n=== Running Predefined Tests ===")
        
        # Start response listener
        listen_task = asyncio.create_task(self.listen_for_responses())
        
        try:
            # Test 1: Text completion
            print("\n1. Testing text-completion service...")
            await self.send_message("text-completion", {
                "system": "You are a helpful assistant.",
                "prompt": "What is 2+2?"
            })
            await asyncio.sleep(2)
            
            # Test 2: Agent
            print("\n2. Testing agent service...")
            await self.send_message("agent", {
                "question": "What is the capital of France?"
            })
            await asyncio.sleep(2)
            
            # Test 3: Embeddings
            print("\n3. Testing embeddings service...")
            await self.send_message("embeddings", {
                "text": "Hello world"
            })
            await asyncio.sleep(2)
            
            # Test 4: Invalid service
            print("\n4. Testing invalid service...")
            await self.send_message("nonexistent-service", {
                "test": "data"
            })
            await asyncio.sleep(2)
            
            print("\nTests completed. Waiting for any remaining responses...")
            await asyncio.sleep(3)
            
        finally:
            listen_task.cancel()
            try:
                await listen_task
            except asyncio.CancelledError:
                pass

async def main():
    parser = argparse.ArgumentParser(
        description="WebSocket Test Client for Reverse Gateway"
    )
    parser.add_argument(
        '--uri',
        default='ws://localhost:8080/in',
        help='WebSocket URI to connect to (default: ws://localhost:8080/in)'
    )
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Run in interactive mode'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    client = TestClient(args.uri)
    
    try:
        await client.connect()
        
        if args.interactive:
            await client.interactive_mode()
        else:
            await client.run_predefined_tests()
            
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        logger.error(f"Client error: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())