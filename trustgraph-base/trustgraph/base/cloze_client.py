
from . request_response_spec import RequestResponseSpec
from .. schema import ClozeRequest, ClozeResponse


class ClozeClient:
    async def predict(self, model, query, timeout=300):

        resp = await self.request(
            ClozeRequest(
                operation="predict",
                model=model,
                query=query,
            ),
            timeout=timeout,
        )

        if resp.error:
            raise RuntimeError(resp.error.message)

        return resp


class ClozeClientSpec(RequestResponseSpec):
    def __init__(
            self, request_name, response_name, optional=False,
    ):
        super(ClozeClientSpec, self).__init__(
            request_name=request_name,
            request_schema=ClozeRequest,
            response_name=response_name,
            response_schema=ClozeResponse,
            impl=ClozeClient,
            optional=optional,
        )
