
import json

from . request_response_spec import RequestResponse, RequestResponseSpec
from .. schema import PromptRequest, PromptResponse

class PromptClient(RequestResponse):

    async def prompt(self, id, variables, timeout=600):

        resp = await self.request(
            PromptRequest(
                id = id,
                terms = {
                    k: json.dumps(v)
                    for k, v in variables.items()
                }
            ),
            timeout=timeout
        )

        if resp.error:
            raise RuntimeError(resp.error.message)

        if resp.text: return resp.text

        return json.loads(resp.object)

    async def extract_definitions(self, text, timeout=600):
        return await self.prompt(
            id = "extract-definitions",
            variables = { "text": text }
        )

    async def extract_relationships(self, text, timeout=600):
        return await self.prompt(
            id = "extract-relationships",
            variables = { "text": text }
        )

class PromptClientSpec(RequestResponseSpec):
    def __init__(
            self, request_name, response_name,
    ):
        super(PromptClientSpec, self).__init__(
            request_name = request_name,
            request_schema = PromptRequest,
            response_name = response_name,
            response_schema = PromptResponse,
            impl = PromptClient,
        )

