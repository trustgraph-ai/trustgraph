
from . request_response_spec import RequestResponseSpec
from .. schema import VerificationRequest, VerificationResponse


class VerificationClient:

    async def verify(
        self, run_id, step_id, expected_type, artifact,
        shape="", timeout=300,
    ):

        resp = await self.request(
            VerificationRequest(
                run_id=run_id,
                step_id=step_id,
                expected_type=expected_type,
                artifact=artifact,
                shape=shape,
            ),
            timeout=timeout,
        )

        if resp.error:
            raise RuntimeError(resp.error.message)

        return resp


class VerificationClientSpec(RequestResponseSpec):
    def __init__(
            self, request_name, response_name, optional=False,
    ):
        super(VerificationClientSpec, self).__init__(
            request_name=request_name,
            request_schema=VerificationRequest,
            response_name=response_name,
            response_schema=VerificationResponse,
            impl=VerificationClient,
            optional=optional,
        )
