
from . request_response_spec import RequestResponseSpec
from .. schema import DecisionScoringRequest, DecisionScoringResponse


class DecisionScoringClient:
    async def score(self, state, questions, timeout=300):

        resp = await self.request(
            DecisionScoringRequest(
                state=state,
                questions=questions,
            ),
            timeout=timeout,
        )

        if resp.error:
            raise RuntimeError(resp.error.message)

        return resp


class DecisionScoringClientSpec(RequestResponseSpec):
    def __init__(
            self, request_name, response_name,
    ):
        super(DecisionScoringClientSpec, self).__init__(
            request_name=request_name,
            request_schema=DecisionScoringRequest,
            response_name=response_name,
            response_schema=DecisionScoringResponse,
            impl=DecisionScoringClient,
        )
