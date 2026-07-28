
from . request_response_client import RequestResponseClient


class AsyncRequestResponseWrapper:

    def __init__(self, backend, request_topic, response_topic,
                 request_schema, response_schema, subscription=None,
                 processor_id=None, target_service=None):
        self._backend = backend
        self._request_topic = request_topic
        self._response_topic = response_topic
        self._request_schema = request_schema
        self._response_schema = response_schema
        self._subscription = subscription
        self._processor_id = processor_id
        self._target_service = target_service
        self._client = None

    async def start(self):
        self._client = await RequestResponseClient.create(
            backend=self._backend,
            request_topic=self._request_topic,
            response_topic=self._response_topic,
            request_schema=self._request_schema,
            response_schema=self._response_schema,
            subscription=self._subscription,
            processor_id=self._processor_id,
            target_service=self._target_service,
        )

    async def request(self, message, timeout=60):
        return await self._client.request(message, timeout=timeout)

    async def stop(self):
        if self._client:
            await self._client.close()
            self._client = None

    async def close(self):
        await self.stop()
