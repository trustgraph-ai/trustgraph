
import _pulsar

from .. schema import AgentRequest, AgentResponse
from .. schema import agent_request_queue
from .. schema import agent_response_queue
from . base import BaseClient

# Ugly
ERROR=_pulsar.LoggerLevel.Error
WARN=_pulsar.LoggerLevel.Warn
INFO=_pulsar.LoggerLevel.Info
DEBUG=_pulsar.LoggerLevel.Debug

class AgentClient(BaseClient):

    def __init__(
            self, log_level=ERROR,
            subscriber=None,
            input_queue=None,
            output_queue=None,
            pulsar_host="pulsar://pulsar:6650",
            pulsar_api_key=None,
    ):

        if input_queue is None: input_queue = agent_request_queue
        if output_queue is None: output_queue = agent_response_queue

        super(AgentClient, self).__init__(
            log_level=log_level,
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
            timeout=300
    ):

        def inspect(x):

            if x.thought and think:
                think(x.thought)
                return

            if x.observation and observe:
                observe(x.observation)
                return

            if x.answer:
                return True

            return False

        return self.call(
            question=question, inspect=inspect, timeout=timeout
        ).answer

