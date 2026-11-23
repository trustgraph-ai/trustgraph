
import json
import logging

from .. schema import (
    RemoteActionRequest, RemoteActionResponse, UserContext,
)
from .. base.serialization import dataclass_to_dict
from . request_response_client import RequestResponseClient

logger = logging.getLogger(__name__)


class RemoteActionClient:

    def __init__(self, backend, request_topic, response_topic):
        self._backend = backend
        self._request_topic = request_topic
        self._response_topic = response_topic
        self._client = None

    async def _ensure_client(self):
        if self._client is None:
            self._client = await RequestResponseClient.create(
                backend=self._backend,
                request_topic=self._request_topic,
                response_topic=self._response_topic,
                request_schema=RemoteActionRequest,
                response_schema=RemoteActionResponse,
            )
        return self._client

    async def call(
        self, run_id, step_id, capability, params,
        input_artifacts=None, user_context=None, timeout=300,
    ):
        client = await self._ensure_client()

        uc_str = ""
        if user_context:
            uc_str = json.dumps(dataclass_to_dict(user_context))

        resp = await client.request(
            RemoteActionRequest(
                run_id=run_id,
                step_id=step_id,
                capability=capability,
                params=json.dumps(params) if params else "{}",
                input_artifacts=(
                    json.dumps(input_artifacts) if input_artifacts else "[]"
                ),
                user_context=uc_str,
            ),
            timeout=timeout,
        )

        if resp.error:
            raise RuntimeError(resp.error.message)

        artifact = json.loads(resp.artifact) if resp.artifact else {}

        return resp.artifact_type, artifact

    async def close(self):
        if self._client:
            await self._client.close()
            self._client = None
