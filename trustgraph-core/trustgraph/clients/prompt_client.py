
import _pulsar

from .. schema import PromptRequest, PromptResponse, Fact, RowSchema, Field
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

    def request_definitions(self, chunk, timeout=300):

        return self.call(
            kind="extract-definitions", chunk=chunk,
            timeout=timeout
        ).definitions
    
    def request_topics(self, chunk, timeout=300):

        return self.call(
            kind="extract-topics", chunk=chunk,
            timeout=timeout
        ).topics

    def request_relationships(self, chunk, timeout=300):

        return self.call(
            kind="extract-relationships", chunk=chunk,
            timeout=timeout
        ).relationships

    def request_rows(self, schema, chunk, timeout=300):

        return self.call(
            kind="extract-rows", chunk=chunk,
            row_schema=RowSchema(
                name=schema.name,
                description=schema.description,
                fields=[
                    Field(
                        name=f.name, type=str(f.type), size=f.size,
                        primary=f.primary, description=f.description,
                    )
                    for f in schema.fields
                ]
            ),
            timeout=timeout
        ).rows

    def request_kg_prompt(self, query, kg, timeout=300):

        return self.call(
            kind="kg-prompt",
            query=query,
            kg=[
                Fact(s=v[0], p=v[1], o=v[2])
                for v in kg
            ],
            timeout=timeout
        ).answer

    def request_document_prompt(self, query, documents, timeout=300):

        return self.call(
            kind="document-prompt",
            query=query,
            documents=documents,
            timeout=timeout
        ).answer

