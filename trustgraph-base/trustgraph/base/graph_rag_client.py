
from . request_response_spec import RequestResponse, RequestResponseSpec
from .. schema import GraphRagQuery, GraphRagResponse

class GraphRagClient(RequestResponse):
    async def rag(self, query, user="trustgraph", collection="default",
                  timeout=600):
        resp = await self.request(
            GraphRagQuery(
                query = query,
                user = user,
                collection = collection,
            ),
            timeout=timeout
        )

        if resp.error:
            raise RuntimeError(resp.error.message)

        return resp.response

class GraphRagClientSpec(RequestResponseSpec):
    def __init__(
            self, request_name, response_name,
    ):
        super(GraphRagClientSpec, self).__init__(
            request_name = request_name,
            request_schema = GraphRagQuery,
            response_name = response_name,
            response_schema = GraphRagResponse,
            impl = GraphRagClient,
        )

