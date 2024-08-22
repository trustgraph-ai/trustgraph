
import pulsar
import _pulsar
from pulsar.schema import JsonSchema
import hashlib
import uuid
import time

from .. schema import TextCompletionRequest, TextCompletionResponse
from .. schema import text_completion_request_queue
from .. schema import text_completion_response_queue
from .. exceptions import *
from . base import BaseClient

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
    ):

        if input_queue is None: input_queue = text_completion_request_queue
        if output_queue is None: output_queue = text_completion_response_queue

        super(LlmClient, self).__init__(
            log_level=log_level,
            subscriber=subscriber,
            input_queue=input_queue,
            output_queue=output_queue,
            pulsar_host=pulsar_host,
            input_schema=TextCompletionRequest,
            output_schema=TextCompletionResponse,
        )

    def request(self, prompt, timeout=30):
        return self.call(prompt=prompt, timeout=timeout).response

