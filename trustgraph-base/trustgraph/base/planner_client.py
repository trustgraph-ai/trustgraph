
from . request_response_spec import RequestResponseSpec
from .. schema import PlannerRequest, PlannerResponse


class PlannerClient:

    async def plan(self, run_id, goal, user_context=None, timeout=300):

        resp = await self.request(
            PlannerRequest(
                run_id=run_id,
                goal=goal,
                user_context=user_context,
            ),
            timeout=timeout,
        )

        if resp.error:
            raise RuntimeError(resp.error.message)

        return resp


class PlannerClientSpec(RequestResponseSpec):
    def __init__(
            self, request_name, response_name, optional=False,
    ):
        super(PlannerClientSpec, self).__init__(
            request_name=request_name,
            request_schema=PlannerRequest,
            response_name=response_name,
            response_schema=PlannerResponse,
            impl=PlannerClient,
            optional=optional,
        )
