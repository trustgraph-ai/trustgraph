
from dataclasses import dataclass
from websockets.asyncio.client import connect
import asyncio
import logging
import json
import uuid
import time

class WebSocketManager:

    def __init__(self, url):
        self.url = url
        self.socket = None

    async def start(self):
        self.socket = await connect(self.url)
        self.pending_requests = {}
        self.running = True
        self.reader_task = asyncio.create_task(self.reader())

    async def stop(self):
        self.running = False
        await self.reader_task

    async def reader(self):
        """
        Background task to read websocket responses and route to correct
        request
        """

        while self.running:
            try:

                try:
                    response_text = await asyncio.wait_for(
                        self.socket.recv(), 0.5
                    )
                except TimeoutError:
                    continue

                response = json.loads(response_text)

                request_id = response.get("id")
                if request_id and request_id in self.pending_requests:
                    # Put the response in the queue
                    queue = self.pending_requests[request_id]
                    await queue.put(response)
                else:
                    logging.warning(
                        f"Response for unknown request ID: {request_id}"
                    )

            except Exception as e:

                logging.error(f"Error in websocket reader: {e}")

                # Put error in all pending queues
                for queue in self.pending_requests.values():
                    try:
                        await queue.put({"error": str(e)})
                    except:
                        pass

                self.pending_requests.clear()
                break

        await self.socket.close()
        self.socket = None

    async def request(
            self, service, request_data, flow_id="default",
    ):
        """
        Send a request via websocket and handle single or streaming responses
        """

        # Generate unique request ID
        request_id = f"{uuid.uuid4()}"

        # Determine if this service streams responses
        streaming_services = {"agent"}
        is_streaming = service in streaming_services

        # Create a queue for all responses (streaming and single)
        response_queue = asyncio.Queue()
        self.pending_requests[request_id] = response_queue

        try:

            # Build request message
            message = {
                "id": request_id,
                "service": service,
                "request": request_data,
            }

            if flow_id is not None:
                message["flow"] = flow_id

            # Send request
            await self.socket.send(json.dumps(message))

            while self.running:

                try:
                    response = await asyncio.wait_for(
                        response_queue.get(), 0.5
                    )
                except TimeoutError:
                    continue

                if "error" in response:
                    if "message" in response["error"]:
                        raise RuntimeError(response["error"]["text"])
                    else:
                        raise RuntimeError(str(response["error"]))

                yield response["response"]

                if "complete" in response:
                    if response["complete"]:
                        break

        except Exception as e:
            # Clean up on error
            self.pending_requests.pop(request_id, None)
            raise e

