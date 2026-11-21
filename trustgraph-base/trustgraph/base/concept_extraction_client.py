
from . request_response_spec import RequestResponseSpec
from .. schema import ConceptExtractionRequest, ConceptExtractionResponse

class ConceptExtractionClient:
    async def extract(self, query, timeout=300):

        resp = await self.request(
            ConceptExtractionRequest(
                query=query,
            ),
            timeout=timeout,
        )

        if resp.error:
            raise RuntimeError(resp.error.message)

        return resp.concepts

class ConceptExtractionClientSpec(RequestResponseSpec):
    def __init__(
            self, request_name, response_name, optional=False,
    ):
        super(ConceptExtractionClientSpec, self).__init__(
            request_name = request_name,
            request_schema = ConceptExtractionRequest,
            response_name = response_name,
            response_schema = ConceptExtractionResponse,
            impl = ConceptExtractionClient,
            optional = optional,
        )
