
from . request_response_spec import RequestResponseSpec
from .. schema import (
    KnowledgeRetrievalRequest, KnowledgeRetrievalResponse,
)

class KnowledgeRetrievalClient:
    async def retrieve(
        self, concepts=None, entities=None,
        entity_limit=50, triple_limit=30,
        max_path_length=2, edge_limit=25,
        max_reranker_input=350,
        languages=None, graph="",
        timeout=300,
    ):

        resp = await self.request(
            KnowledgeRetrievalRequest(
                concepts=concepts or [],
                entities=entities or [],
                entity_limit=entity_limit,
                triple_limit=triple_limit,
                max_path_length=max_path_length,
                edge_limit=edge_limit,
                max_reranker_input=max_reranker_input,
                languages=languages or [],
                graph=graph,
            ),
            timeout=timeout,
        )

        if resp.error:
            raise RuntimeError(resp.error.message)

        return resp

class KnowledgeRetrievalClientSpec(RequestResponseSpec):
    def __init__(
            self, request_name, response_name,
    ):
        super(KnowledgeRetrievalClientSpec, self).__init__(
            request_name = request_name,
            request_schema = KnowledgeRetrievalRequest,
            response_name = response_name,
            response_schema = KnowledgeRetrievalResponse,
            impl = KnowledgeRetrievalClient,
        )
