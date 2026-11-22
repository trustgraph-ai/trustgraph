
from . request_response_spec import RequestResponseSpec
from .. schema import PolicyEngineRequest, PolicyEngineResponse


class PolicyEngineClient:

    async def evaluate(
        self, run_id, step_id, evaluation_type, subject,
        user_context=None, timeout=300,
    ):

        resp = await self.request(
            PolicyEngineRequest(
                run_id=run_id,
                step_id=step_id,
                evaluation_type=evaluation_type,
                subject=subject,
                user_context=user_context,
            ),
            timeout=timeout,
        )

        if resp.error:
            raise RuntimeError(resp.error.message)

        return resp


class PolicyEngineClientSpec(RequestResponseSpec):
    def __init__(
            self, request_name, response_name, optional=False,
    ):
        super(PolicyEngineClientSpec, self).__init__(
            request_name=request_name,
            request_schema=PolicyEngineRequest,
            response_name=response_name,
            response_schema=PolicyEngineResponse,
            impl=PolicyEngineClient,
            optional=optional,
        )
