from __future__ import annotations

from . request_response_spec import RequestResponseSpec
from .. schema import SparqlQueryRequest, SparqlQueryResponse


class SparqlClient:

    async def query(self, query, collection="default", limit=10000,
                    timeout=300):
        resp = await self.request(
            SparqlQueryRequest(
                query=query,
                collection=collection,
                limit=limit,
            ),
            timeout=timeout,
        )

        if resp.error:
            raise RuntimeError(resp.error.message)

        return resp


class SparqlClientSpec(RequestResponseSpec):
    def __init__(
            self, request_name, response_name,
    ):
        super(SparqlClientSpec, self).__init__(
            request_name=request_name,
            request_schema=SparqlQueryRequest,
            response_name=response_name,
            response_schema=SparqlQueryResponse,
            impl=SparqlClient,
        )
