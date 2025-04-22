
from . request_response_spec import RequestResponse, RequestResponseSpec
from .. schema import AgentRequest, AgentResponse
from .. knowledge import Uri, Literal

class AgentClient(RequestResponse):
    async def request(self, recipient, question, plan=None, state=None,
                    history=[], timeout=300):

        resp = await self.request(
            AgentRequest(
                question = question,
                plan = plan,
                state = state,
                history = history,
            ),
            recipient=recipient,
            timeout=timeout,
        )

        print(resp, flush=True)

        if resp.error:
            raise RuntimeError(resp.error.message)

        return resp

class GraphEmbeddingsClientSpec(RequestResponseSpec):
    def __init__(
            self, request_name, response_name,
    ):
        super(GraphEmbeddingsClientSpec, self).__init__(
            request_name = request_name,
            request_schema = GraphEmbeddingsRequest,
            response_name = response_name,
            response_schema = GraphEmbeddingsResponse,
            impl = GraphEmbeddingsClient,
        )

