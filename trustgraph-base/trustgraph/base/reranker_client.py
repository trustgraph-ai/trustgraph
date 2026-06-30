
from . request_response_spec import RequestResponse, RequestResponseSpec
from .. schema import (
    RerankerRequest, RerankerResponse,
    RerankerQuery, RerankerDocument,
)

class RerankerClient(RequestResponse):
    async def rerank(self, queries, documents, limit=10, timeout=300):

        resp = await self.request(
            RerankerRequest(
                queries=[
                    RerankerQuery(query_id=q["id"], query_text=q["text"])
                    for q in queries
                ],
                documents=[
                    RerankerDocument(
                        document_id=d["id"], document_text=d["text"]
                    )
                    for d in documents
                ],
                limit=limit,
            ),
            timeout=timeout
        )

        if resp.error:
            raise RuntimeError(resp.error.message)

        return resp.results

class RerankerClientSpec(RequestResponseSpec):
    def __init__(
            self, request_name, response_name,
    ):
        super(RerankerClientSpec, self).__init__(
            request_name = request_name,
            request_schema = RerankerRequest,
            response_name = response_name,
            response_schema = RerankerResponse,
            impl = RerankerClient,
        )
