
import json

from . request_response_spec import RequestResponse, RequestResponseSpec
from .. schema import ToolRequest, ToolResponse

class ToolClient(RequestResponse):

    async def invoke(self, name, parameters={}, timeout=600):

        if parameters is None:
            parameters = {}

        resp = await self.request(
            ToolRequest(
                name = name,
                parameters = json.dumps(parameters),
            ),
            timeout=timeout
        )

        if resp.error:
            raise RuntimeError(resp.error.message)

        if resp.text: return resp.text

        return json.loads(resp.object)

class ToolClientSpec(RequestResponseSpec):
    def __init__(
            self, request_name, response_name,
    ):
        super(ToolClientSpec, self).__init__(
            request_name = request_name,
            request_schema = ToolRequest,
            response_name = response_name,
            response_schema = ToolResponse,
            impl = ToolClient,
        )

