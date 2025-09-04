from . request_response_spec import RequestResponse, RequestResponseSpec
from .. schema import StructuredQueryRequest, StructuredQueryResponse

class StructuredQueryClient(RequestResponse):
    async def structured_query(self, question, timeout=600):
        resp = await self.request(
            StructuredQueryRequest(
                question = question
            ),
            timeout=timeout
        )

        if resp.error:
            raise RuntimeError(resp.error.message)

        # Return the full response structure for the tool to handle
        return {
            "data": resp.data,
            "errors": resp.errors if resp.errors else [],
            "error": resp.error
        }

class StructuredQueryClientSpec(RequestResponseSpec):
    def __init__(
            self, request_name, response_name,
    ):
        super(StructuredQueryClientSpec, self).__init__(
            request_name = request_name,
            request_schema = StructuredQueryRequest,
            response_name = response_name,
            response_schema = StructuredQueryResponse,
            impl = StructuredQueryClient,
        )