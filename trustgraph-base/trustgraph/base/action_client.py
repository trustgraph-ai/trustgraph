
from . request_response_spec import RequestResponseSpec
from .. schema import ActionRequest, ActionResponse


class ActionClient:

    async def execute(
        self, run_id, step_id, capability, params,
        user_context=None, timeout=300,
    ):

        resp = await self.request(
            ActionRequest(
                run_id=run_id,
                step_id=step_id,
                capability=capability,
                params=params,
                user_context=user_context,
            ),
            timeout=timeout,
        )

        if resp.error:
            raise RuntimeError(resp.error.message)

        return resp


class ActionClientSpec(RequestResponseSpec):
    def __init__(
            self, request_name, response_name, optional=False,
    ):
        super(ActionClientSpec, self).__init__(
            request_name=request_name,
            request_schema=ActionRequest,
            response_name=response_name,
            response_schema=ActionResponse,
            impl=ActionClient,
            optional=optional,
        )
