
import pulsar
import _pulsar
from pulsar.schema import JsonSchema
import hashlib
import uuid
import time

from .. schema import PromptRequest, PromptResponse, Fact
from .. schema import prompt_request_queue
from .. schema import prompt_response_queue
from . base import BaseClient

# Ugly
ERROR=_pulsar.LoggerLevel.Error
WARN=_pulsar.LoggerLevel.Warn
INFO=_pulsar.LoggerLevel.Info
DEBUG=_pulsar.LoggerLevel.Debug

class PromptClient(BaseClient):

    def __init__(
            self, log_level=ERROR,
            subscriber=None,
            input_queue=None,
            output_queue=None,
            pulsar_host="pulsar://pulsar:6650",
    ):

        if input_queue == None:
            input_queue = prompt_request_queue

        if output_queue == None:
            output_queue = prompt_response_queue

        super(PromptClient, self).__init__(
            log_level=log_level,
            subscriber=subscriber,
            input_queue=input_queue,
            output_queue=output_queue,
            pulsar_host=pulsar_host,
            input_schema=PromptRequest,
            output_schema=PromptResponse,
        )

    def request_definitions(self, chunk, timeout=30):

        return self.call(kind="extract-definitions", chunk=chunk,
                         timeout=timeout).definitions

    def request_relationships(self, chunk, timeout=30):

        return self.call(kind="extract-relationships", chunk=chunk,
                         timeout=timeout).relationships

    def request_kg_prompt(self, query, kg, timeout=30):

        return self.call(
            kind="kg-prompt",
            query=query,
            kg=[
                Fact(s=v[0], p=v[1], o=v[2])
                for v in kg
            ],
            timeout=timeout
        ).answer

