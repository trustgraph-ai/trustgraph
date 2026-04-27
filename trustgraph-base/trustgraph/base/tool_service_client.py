
import json
import logging

from . request_response_spec import RequestResponse, RequestResponseSpec
from .. schema import ToolServiceRequest, ToolServiceResponse

logger = logging.getLogger(__name__)


class ToolServiceClient(RequestResponse):
    """Client for invoking dynamically configured tool services."""

    async def call(self, config, arguments, timeout=600):
        """
        Call a tool service.

        Args:
            config: Dict of config values (e.g., {"collection": "customers"})
            arguments: Dict of arguments from LLM
            timeout: Request timeout in seconds

        Returns:
            Response string from the tool service
        """
        resp = await self.request(
            ToolServiceRequest(
                config=json.dumps(config) if config else "{}",
                arguments=json.dumps(arguments) if arguments else "{}",
            ),
            timeout=timeout
        )

        if resp.error:
            raise RuntimeError(resp.error.message)

        return resp.response

    async def call_streaming(self, config, arguments, callback, timeout=600):
        """
        Call a tool service with streaming response.

        Args:
            config: Dict of config values
            arguments: Dict of arguments from LLM
            callback: Async function called with each response chunk
            timeout: Request timeout in seconds

        Returns:
            Final response string
        """
        result = []

        async def handle_response(resp):
            if resp.error:
                raise RuntimeError(resp.error.message)

            if resp.response:
                result.append(resp.response)
                await callback(resp.response)

            return resp.end_of_stream

        await self.request(
            ToolServiceRequest(
                config=json.dumps(config) if config else "{}",
                arguments=json.dumps(arguments) if arguments else "{}",
            ),
            timeout=timeout,
            recipient=handle_response
        )

        return "".join(result)


class ToolServiceClientSpec(RequestResponseSpec):
    """Specification for a tool service client."""

    def __init__(self, request_name, response_name):
        super(ToolServiceClientSpec, self).__init__(
            request_name=request_name,
            request_schema=ToolServiceRequest,
            response_name=response_name,
            response_schema=ToolServiceResponse,
            impl=ToolServiceClient,
        )
