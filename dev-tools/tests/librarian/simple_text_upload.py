#!/usr/bin/env python3
"""
Minimal example: upload a small text document via websocket API
"""

import asyncio
import json
import base64
import time
import websockets

async def main():
    url = "ws://localhost:8088/api/v1/socket"

    # Small text content
    content = b"AAAAAAAAAABBBBBBBBBBCCCCCCCCCC"

    request_id = 0

    async def send_request(ws, request):
        nonlocal request_id
        request_id += 1
        msg = {
            "id": f"req-{request_id}",
            "service": "librarian",
            "request": request
        }
        await ws.send(json.dumps(msg))
        response = json.loads(await ws.recv())
        if "error" in response:
            raise Exception(response["error"])
        return response.get("response", {})

    async with websockets.connect(url) as ws:

        print(f"Uploading {len(content)} bytes...")

        resp = await send_request(ws, {
            "operation": "add-document",
            "document-metadata": {
                "id": "test-chunked-doc-001",
                "time": int(time.time()),
                "kind": "text/plain",
                "title": "My Test Document",
                "comments": "Small doc for chunk testing",
                "user": "trustgraph",
                "tags": ["test"],
                "metadata": [],
            },
            "content": base64.b64encode(content).decode("utf-8"),
        })

        print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
