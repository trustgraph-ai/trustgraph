
import logging

logger = logging.getLogger("sender")
logger.setLevel(logging.INFO)

class ServiceSender:

    def __init__(
            self,
            backend,
            queue, schema,
    ):

        self.backend = backend
        self.queue = queue
        self.schema = schema
        self.producer = None

    async def start(self):
        self.producer = await self.backend.create_producer(
            topic=self.queue,
            schema=self.schema,
        )

    async def stop(self):
        if self.producer:
            await self.producer.close()
            self.producer = None

    def to_request(self, request):
        raise RuntimeError("Not defined")

    async def process(self, request, responder=None):

        try:

            await self.producer.send(self.to_request(request))

            if responder:
                await responder({}, True)

            return {}

        except Exception as e:

            logging.error(f"Exception: {e}")

            err = { "error": str(e) }

            if responder:
                await responder(err, True)

            return err
