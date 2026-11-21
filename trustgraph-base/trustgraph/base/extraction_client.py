from dataclasses import dataclass, field

from . request_response_spec import RequestResponseSpec
from .. schema import ExtractionRequest, ExtractionResponse, Triple, EntityContext


@dataclass
class ExtractionResult:
    triples: list[Triple] = field(default_factory=list)
    entity_contexts: list[EntityContext] = field(default_factory=list)
    provenance_triples: list[Triple] = field(default_factory=list)


class ExtractionClient:
    async def extract(self, text, document_id="", timeout=300):

        result = ExtractionResult()

        async def recipient(resp):
            if resp.error:
                raise RuntimeError(resp.error.message)

            if resp.kind == "triples":
                result.triples.extend(resp.triples)
            elif resp.kind == "entity-contexts":
                result.entity_contexts.extend(resp.entity_contexts)
            elif resp.kind == "provenance":
                result.provenance_triples.extend(resp.triples)

            return resp.end_of_stream

        await self.request(
            ExtractionRequest(
                text=text,
                document_id=document_id,
            ),
            timeout=timeout,
            recipient=recipient,
        )

        return result


class ExtractionClientSpec(RequestResponseSpec):
    def __init__(
            self, request_name, response_name,
    ):
        super(ExtractionClientSpec, self).__init__(
            request_name=request_name,
            request_schema=ExtractionRequest,
            response_name=response_name,
            response_schema=ExtractionResponse,
            impl=ExtractionClient,
        )
