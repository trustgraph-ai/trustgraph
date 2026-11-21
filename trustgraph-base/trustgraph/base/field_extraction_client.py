
from . request_response_spec import RequestResponseSpec
from .. schema import FieldExtractionRequest, FieldExtractionResponse


class FieldExtractionClient:
    async def extract(self, state, fields, timeout=300):

        resp = await self.request(
            FieldExtractionRequest(
                state=state,
                fields=fields,
            ),
            timeout=timeout,
        )

        if resp.error:
            raise RuntimeError(resp.error.message)

        return resp


class FieldExtractionClientSpec(RequestResponseSpec):
    def __init__(
            self, request_name, response_name, optional=False,
    ):
        super(FieldExtractionClientSpec, self).__init__(
            request_name=request_name,
            request_schema=FieldExtractionRequest,
            response_name=response_name,
            response_schema=FieldExtractionResponse,
            impl=FieldExtractionClient,
            optional=optional,
        )
