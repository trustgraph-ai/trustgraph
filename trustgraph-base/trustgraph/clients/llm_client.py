
import _pulsar

from .. schema import TextCompletionRequest, TextCompletionResponse
from .. schema import text_completion_request_queue
from .. schema import text_completion_response_queue
from . base import BaseClient
from .. exceptions import LlmError

# Ugly
ERROR=_pulsar.LoggerLevel.Error
WARN=_pulsar.LoggerLevel.Warn
INFO=_pulsar.LoggerLevel.Info
DEBUG=_pulsar.LoggerLevel.Debug

class LlmClient(BaseClient):

    def __init__(
            self, log_level=ERROR,
            subscriber=None,
            input_queue=None,
            output_queue=None,
            pulsar_host="pulsar://pulsar:6650",
            pulsar_api_key=None,
    ):

        if input_queue is None: input_queue = text_completion_request_queue
        if output_queue is None: output_queue = text_completion_response_queue

        super(LlmClient, self).__init__(
            log_level=log_level,
            subscriber=subscriber,
            input_queue=input_queue,
            output_queue=output_queue,
            pulsar_host=pulsar_host,
            pulsar_api_key=pulsar_api_key,
            input_schema=TextCompletionRequest,
            output_schema=TextCompletionResponse,
        )

    def request(self, system, prompt, timeout=300, streaming=False):
        """
        Non-streaming request (backward compatible).
        Returns complete response string.
        """
        if streaming:
            raise ValueError("Use request_stream() for streaming requests")
        return self.call(
            system=system, prompt=prompt, streaming=False, timeout=timeout
        ).response

    def request_stream(self, system, prompt, timeout=300):
        """
        Streaming request generator.
        Yields response chunks as they arrive.
        Usage:
            for chunk in client.request_stream(system, prompt):
                print(chunk.response, end='', flush=True)
        """
        import time
        import uuid

        id = str(uuid.uuid4())
        request = TextCompletionRequest(
            system=system, prompt=prompt, streaming=True
        )

        end_time = time.time() + timeout
        self.producer.send(request, properties={"id": id})

        # Collect responses until end_of_stream
        while time.time() < end_time:
            try:
                msg = self.consumer.receive(timeout_millis=2500)
            except Exception:
                continue

            mid = msg.properties()["id"]

            if mid == id:
                value = msg.value()

                # Handle errors
                if value.error:
                    self.consumer.acknowledge(msg)
                    if value.error.type == "llm-error":
                        raise LlmError(value.error.message)
                    else:
                        raise RuntimeError(
                            f"{value.error.type}: {value.error.message}"
                        )

                self.consumer.acknowledge(msg)
                yield value

                # Check if this is the final chunk
                if getattr(value, 'end_of_stream', True):
                    break
            else:
                # Ignore messages with wrong ID
                self.consumer.acknowledge(msg)

        if time.time() >= end_time:
            raise TimeoutError("Timed out waiting for response")

