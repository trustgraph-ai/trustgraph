

from .. schema import AgentRequest, AgentResponse
from .. schema import agent_request_queue
from .. schema import agent_response_queue
from . base import BaseClient

# Ugly

class AgentClient(BaseClient):

    def __init__(
            self,
            subscriber=None,
            input_queue=None,
            output_queue=None,
            pulsar_host="pulsar://pulsar:6650",
            pulsar_api_key=None,
    ):

        if input_queue is None: input_queue = agent_request_queue
        if output_queue is None: output_queue = agent_response_queue

        super(AgentClient, self).__init__(
            subscriber=subscriber,
            input_queue=input_queue,
            output_queue=output_queue,
            pulsar_host=pulsar_host,
            input_schema=AgentRequest,
            output_schema=AgentResponse,
            pulsar_api_key=pulsar_api_key
        )

    def request(
            self,
            question,
            think=None,
            observe=None,
            answer_callback=None,
            error_callback=None,
            timeout=300
    ):
        """
        Request an agent query with optional streaming callbacks.

        Args:
            question: The question to ask
            think: Optional callback(content, end_of_message) for thought chunks
            observe: Optional callback(content, end_of_message) for observation chunks
            answer_callback: Optional callback(content, end_of_message) for answer chunks
            error_callback: Optional callback(content) for error messages
            timeout: Request timeout in seconds

        Returns:
            Complete answer text (accumulated from all answer chunks)
        """
        accumulated_answer = []

        def inspect(x):
            # Handle errors
            if x.message_type == 'error' or x.error:
                if error_callback:
                    error_callback(x.content or (x.error.message if x.error else ""))
                # Continue to check end_of_dialog

            # Handle thought chunks
            elif x.message_type == 'thought':
                if think:
                    think(x.content, x.end_of_message)

            # Handle observation chunks
            elif x.message_type == 'observation':
                if observe:
                    observe(x.content, x.end_of_message)

            # Handle answer chunks
            elif x.message_type == 'answer':
                if x.content:
                    accumulated_answer.append(x.content)
                if answer_callback:
                    answer_callback(x.content, x.end_of_message)

            # Complete when dialog ends
            if x.end_of_dialog:
                return True

            return False  # Continue receiving

        self.call(
            question=question, inspect=inspect, timeout=timeout
        )

        return "".join(accumulated_answer)

