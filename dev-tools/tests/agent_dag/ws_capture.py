#!/usr/bin/env python3
"""
Connect to TrustGraph websocket, run an agent query, capture all
response messages to a JSON file.

Usage:
    python ws_capture.py -q "What is the document about?" -o trace.json
    python ws_capture.py -q "..." -u http://localhost:8088/ -o out.json
"""

import argparse
import asyncio
import json
import os
import websockets

DEFAULT_URL = os.getenv("TRUSTGRAPH_URL", "http://localhost:8088/")
DEFAULT_USER = "trustgraph"
DEFAULT_COLLECTION = "default"
DEFAULT_FLOW = "default"


async def capture(url, flow, question, user, collection, output):

    # Convert to ws URL
    ws_url = url.replace("http://", "ws://").replace("https://", "wss://")
    ws_url = f"{ws_url.rstrip('/')}/api/v1/socket"

    async with websockets.connect(ws_url, ping_interval=20, ping_timeout=120) as ws:

        request = {
            "id": "capture",
            "service": "agent",
            "flow": flow,
            "request": {
                "question": question,
                "user": user,
                "collection": collection,
                "streaming": True,
            },
        }

        await ws.send(json.dumps(request))

        messages = []

        async for raw in ws:
            msg = json.loads(raw)

            if msg.get("id") != "capture":
                continue

            messages.append(msg)

            if msg.get("complete"):
                break

    with open(output, "w") as f:
        json.dump(messages, f, indent=2)

    print(f"Captured {len(messages)} messages to {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-q", "--question", required=True)
    parser.add_argument("-o", "--output", default="trace.json")
    parser.add_argument("-u", "--url", default=DEFAULT_URL)
    parser.add_argument("-f", "--flow", default=DEFAULT_FLOW)
    parser.add_argument("-U", "--user", default=DEFAULT_USER)
    parser.add_argument("-C", "--collection", default=DEFAULT_COLLECTION)
    args = parser.parse_args()

    asyncio.run(capture(
        args.url, args.flow, args.question,
        args.user, args.collection, args.output,
    ))


if __name__ == "__main__":
    main()
