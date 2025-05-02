
import asyncio

from . embeddings import EmbeddingsRequestor

class TestDispatcher:
    def __init__(self, pulsar_client, timeout=120):
        self.pulsar_client = pulsar_client
        timeout = timeout
    async def process(self, data, responder):
        result = { "result": "Hello world!" }

        if responder:
            await responder(result, True)

        return result

class TestDispatcher2:
    def __init__(self, pulsar_client, timeout=120):
        self.pulsar_client = pulsar_client
        timeout = timeout
    async def process(self, data, responder, params):

        thing = params['thing']

        result = { "result": "Hello world!!", "thing": thing }

        if responder:
            await responder(result, True)

        return result

class TestDispatcher3:
    def __init__(self, pulsar_client, timeout=120):
        self.pulsar_client = pulsar_client
        self.timeout = timeout

    async def dispatch(self, ws, running, request):

        class Runner:
            def __init__(self, ws, running):
                self.ws = ws
                self.running = running

            async def destroy(self):

                if self.ws:
                    await self.ws.close()
                    self.ws = None

                self.running.stop()

            async def run(self):

                i = 0

                while self.running.get():
                    await self.ws.send_json({"i": i})
                    i += 1
                    await asyncio.sleep(1)

                await self.ws.close()
                self.ws = None

            async def receive(self, msg):
                print("Receive:", msg.data)

        return Runner(ws, running)

class DispatcherManager:

    def __init__(self, pulsar_client, config_receiver):
        self.pulsar_client = pulsar_client
        self.config_receiver = config_receiver
        self.config_receiver.add_handler(self)

        self.flows = {}
        self.dispatchers = {}

    async def start_flow(self, id, flow):
        print("Start flow", id)
        self.flows[id] = flow
        return

    async def stop_flow(self, id, flow):
        print("Stop flow", id)
        del self.flows[id]
        return

    def dispatch_test_service(self):
        return TestDispatcher(pulsar_client = self.pulsar_client)

    def dispatch_flow_service(self):
#        return TestDispatcher2(pulsar_client = self.pulsar_client)
        return self

    def dispatch_socket_service(self):
        return TestDispatcher3(pulsar_client = self.pulsar_client).dispatch

    async def process(self, data, responder, params):

        flow = params.get("flow")
        kind = params.get("kind")

        key = (flow, kind)

        if flow not in self.flows:
            raise RuntimeError("Invalid flow")

        if key in self.dispatchers:
            return await self.dispatchers[key].process(data, responder)

        qconfig = self.flows[flow]["interfaces"]["embeddings"]

        dispatcher = EmbeddingsRequestor(
            pulsar_client = self.pulsar_client,
            request_queue = qconfig["request"],
            response_queue = qconfig["response"],
            timeout = 120,
            consumer = f"api-gateway-{flow}-{kind}-request",
            subscriber = f"api-gateway-{flow}-{kind}-request",
        )

        await dispatcher.start()

        self.dispatchers[key] = dispatcher

        print("CREATE")
        return await dispatcher.process(data, responder)

