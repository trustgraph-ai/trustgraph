
from . request_response_spec import RequestResponseSpec
from .. schema import QueryFormulationRequest, QueryFormulationResponse


class QueryFormulationClient:

    async def formulate(self, question, schema_name, timeout=300):

        resp = await self.request(
            QueryFormulationRequest(
                mode="formulate",
                question=question,
                schema_name=schema_name,
            ),
            timeout=timeout,
        )

        if resp.error:
            raise RuntimeError(resp.error.message)

        return resp.query_spec

    async def summarise(self, query_spec, goal, timeout=300):

        resp = await self.request(
            QueryFormulationRequest(
                mode="summarise",
                question=goal,
                query_spec=query_spec,
            ),
            timeout=timeout,
        )

        if resp.error:
            raise RuntimeError(resp.error.message)

        return resp.query_spec


class QueryFormulationClientSpec(RequestResponseSpec):
    def __init__(
            self, request_name, response_name, optional=False,
    ):
        super(QueryFormulationClientSpec, self).__init__(
            request_name=request_name,
            request_schema=QueryFormulationRequest,
            response_name=response_name,
            response_schema=QueryFormulationResponse,
            impl=QueryFormulationClient,
            optional=optional,
        )
