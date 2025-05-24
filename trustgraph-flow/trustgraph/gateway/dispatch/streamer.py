
import asyncio
import uuid
import logging

from ... base import Publisher
from ... base import Subscriber

logger = logging.getLogger("requestor")
logger.setLevel(logging.INFO)

class ServiceRequestor:

    def __init__(
            self,
            pulsar_client,
            queue, schema,
            handler,
            subscription="api-gateway", consumer_name="api-gateway",
            timeout=600,
    ):

        self.sub = Subscriber(
            pulsar_client, queue,
            subscription, consumer_name,
            schema
        )

        self.timeout = timeout

        self.running = True

        self.receiver = handler

    async def start(self):
        await self.sub.start()
        self.streamer = asyncio.create_task(self.stream())
        sub.start()
        self.running = True

    async def stop(self):
        await self.sub.stop()
        self.running = False

    def from_inbound(self, response):
        raise RuntimeError("Not defined")

    async def stream(self):

        id = str(uuid.uuid4())

        try:

            q = await self.sub.subscribe(id)

            while self.running:

                try:
                    resp = await asyncio.wait_for(
                        q.get(), timeout=self.timeout
                    )
                except Exception as e:
                    raise RuntimeError("Timeout")

                if resp.error:
                    err = { "error": {
                        "type": resp.error.type,
                        "message": resp.error.message,
                    } }

                    fin = False

                    await self.receiver(err, fin)

                else:

                    resp, fin = self.from_inbound(resp)

                    await self.receiver(resp, fin)

                if fin: break

        except Exception as e:

            logging.error(f"Exception: {e}")

            err = { "error": {
                "type": "gateway-error",
                "message": str(e),
            } }
            if responder:
                await responder(err, True)
            return err

        finally:
            await self.sub.unsubscribe(id)

