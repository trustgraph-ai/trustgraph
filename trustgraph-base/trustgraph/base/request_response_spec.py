
import uuid
import asyncio

from . subscriber import Subscriber
from . producer import Producer
from . spec import Spec
from . metrics import ConsumerMetrics, ProducerMetrics

class RequestResponse(Subscriber):

    def __init__(
            self, client, subscription, consumer_name,
            request_topic, request_schema,
            request_metrics,
            response_topic, response_schema,
            response_metrics,
    ):

        super(RequestResponse, self).__init__(
            client = client,
            subscription = subscription,
            consumer_name = consumer_name,
            topic = response_topic,
            schema = response_schema,
        )

        self.producer = Producer(
            client = client,
            topic = request_topic,
            schema = request_schema,
            metrics = request_metrics,
        )

    async def start(self):
        await self.producer.start()
        await super(RequestResponse, self).start()

    async def stop(self):
        await self.producer.stop()
        await super(RequestResponse, self).stop()

    async def request(self, req, timeout=300, recipient=None):

        id = str(uuid.uuid4())

        print("Request", id, "...", flush=True)

        q = await self.subscribe(id)

        try:

            await self.producer.send(
                req,
                properties={"id": id}
            )

        except Exception as e:

            print("Exception:", e)
            raise e


        try:

            while True:

                resp = await asyncio.wait_for(
                    q.get(),
                    timeout=timeout
                )

                print("Got response.", flush=True)

                if recipient is None:

                    # If no recipient handler, just return the first
                    # response we get
                    return resp
                else:

                    # Recipient handler gets to decide when we're done b
                    # returning a boolean
                    fin = await recipient(resp)

                    # If done, return the last result otherwise loop round for
                    # next response
                    if fin:
                        return resp
                    else:
                        continue

        except Exception as e:

            print("Exception:", e)
            raise e

        finally:

            await self.unsubscribe(id)

# This deals with the request/response case.  The caller needs to
# use another service in request/response mode.  Uses two topics:
# - we send on the request topic as a producer
# - we receive on the response topic as a subscriber
class RequestResponseSpec(Spec):
    def __init__(
            self, request_name, request_schema, response_name,
            response_schema, impl=RequestResponse
    ):
        self.request_name = request_name
        self.request_schema = request_schema
        self.response_name = response_name
        self.response_schema = response_schema
        self.impl = impl

    def add(self, flow, processor, definition):

        producer_metrics = ProducerMetrics(
            flow.id, f"{flow.name}-{self.response_name}"
        )

        rr = self.impl(
            client = processor.client,
            subscription = flow.id,
            consumer_name = flow.id,
            request_topic = definition[self.request_name],
            request_schema = self.request_schema,
            request_metrics = producer_metrics,
            response_topic = definition[self.response_name],
            response_schema = self.response_schema,
            response_metrics = None,
        )

        flow.consumer[self.request_name] = rr

