#!/usr/bin/env python3
"""
Minimal example: download a text document in tiny chunks via websocket API
"""

import asyncio
import json
import base64
import websockets

async def main():
    url = "ws://localhost:8088/api/v1/socket"

    document_id = "test-chunked-doc-001"
    chunk_size = 10  # Tiny chunks!

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

        print(f"Fetching document: {document_id}")
        print(f"Chunk size: {chunk_size} bytes")
        print()

        chunk_index = 0
        all_content = b""

        while True:
            resp = await send_request(ws, {
                "operation": "stream-document",
                "user": "trustgraph",
                "document-id": document_id,
                "chunk-index": chunk_index,
                "chunk-size": chunk_size,
            })

            chunk_data = base64.b64decode(resp["content"])
            total_chunks = resp["total-chunks"]
            total_bytes = resp["total-bytes"]

            print(f"Chunk {chunk_index}: {chunk_data}")

            all_content += chunk_data
            chunk_index += 1

            if chunk_index >= total_chunks:
                break

        print()
        print(f"Complete: {all_content}")

if __name__ == "__main__":
    asyncio.run(main())
