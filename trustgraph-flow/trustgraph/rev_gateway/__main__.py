import asyncio
import argparse
import logging
import sys
import os
from .service import ReverseGateway

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def parse_args():
    parser = argparse.ArgumentParser(
        prog="reverse-gateway",
        description="TrustGraph Reverse Gateway - WebSocket to Pulsar bridge"
    )
    
    parser.add_argument(
        '--websocket-uri',
        default=None,
        help='WebSocket URI to connect to (default: wss://api.trustgraph.ai/ws or WEBSOCKET_URI env var)'
    )
    
    parser.add_argument(
        '--max-workers',
        type=int,
        default=10,
        help='Maximum concurrent message handlers (default: 10)'
    )
    
    parser.add_argument(
        '--pulsar-host',
        default=None,
        help='Pulsar host URL (default: pulsar://pulsar:6650 or PULSAR_HOST env var)'
    )
    
    parser.add_argument(
        '--pulsar-api-key',
        default=None,
        help='Pulsar API key for authentication (default: PULSAR_API_KEY env var)'
    )
    
    parser.add_argument(
        '--pulsar-listener',
        default=None,
        help='Pulsar listener name'
    )
    
    return parser.parse_args()

async def main():
    args = parse_args()
    
    gateway = ReverseGateway(
        websocket_uri=args.websocket_uri,
        max_workers=args.max_workers,
        pulsar_host=args.pulsar_host,
        pulsar_api_key=args.pulsar_api_key,
        pulsar_listener=args.pulsar_listener
    )
    
    print(f"Starting reverse gateway:")
    print(f"  WebSocket URI: {gateway.url}")
    print(f"  Max workers: {args.max_workers}")
    print(f"  Pulsar host: {gateway.pulsar_host}")
    
    try:
        await gateway.run()
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())