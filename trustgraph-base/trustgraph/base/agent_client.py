
from . request_response_spec import RequestResponse, RequestResponseSpec
from .. schema import AgentRequest, AgentResponse
from .. knowledge import Uri, Literal

class AgentClient(RequestResponse):
    async def invoke(self, question, plan=None, state=None,
                    history=[], think=None, observe=None, answer_callback=None,
                    timeout=300):
        """
        Invoke the agent with optional streaming callbacks.

        Args:
            question: The question to ask
            plan: Optional plan context
            state: Optional state context
            history: Conversation history
            think: Optional async callback(content, end_of_message) for thought chunks
            observe: Optional async callback(content, end_of_message) for observation chunks
            answer_callback: Optional async callback(content, end_of_message) for answer chunks
            timeout: Request timeout in seconds

        Returns:
            Complete answer text (accumulated from all answer chunks)
        """
        accumulated_answer = []

        async def recipient(resp):
            if resp.error:
                raise RuntimeError(resp.error.message)

            # Handle thought chunks
            if resp.chunk_type == 'thought':
                if think:
                    await think(resp.content, resp.end_of_message)
                return False  # Continue receiving

            # Handle observation chunks
            if resp.chunk_type == 'observation':
                if observe:
                    await observe(resp.content, resp.end_of_message)
                return False  # Continue receiving

            # Handle answer chunks
            if resp.chunk_type == 'answer':
                if resp.content:
                    accumulated_answer.append(resp.content)
                if answer_callback:
                    await answer_callback(resp.content, resp.end_of_message)

            # Complete when dialog ends
            if resp.end_of_dialog:
                return True

            return False  # Continue receiving

        await self.request(
            AgentRequest(
                question = question,
                state = state or "",
                history = history,
            ),
            recipient=recipient,
            timeout=timeout,
        )

        return "".join(accumulated_answer)

class AgentClientSpec(RequestResponseSpec):
    def __init__(
            self, request_name, response_name,
    ):
        super(AgentClientSpec, self).__init__(
            request_name = request_name,
            request_schema = AgentRequest,
            response_name = response_name,
            response_schema = AgentResponse,
            impl = AgentClient,
        )

