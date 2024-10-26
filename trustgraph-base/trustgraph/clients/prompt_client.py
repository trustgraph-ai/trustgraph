
import _pulsar
import json
import dataclasses

from .. schema import PromptRequest, PromptResponse
from .. schema import prompt_request_queue
from .. schema import prompt_response_queue
from . base import BaseClient

# Ugly
ERROR=_pulsar.LoggerLevel.Error
WARN=_pulsar.LoggerLevel.Warn
INFO=_pulsar.LoggerLevel.Info
DEBUG=_pulsar.LoggerLevel.Debug

@dataclasses.dataclass
class Definition:
    name: str
    definition: str

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

    def request(self, id, terms, timeout=300):

        resp = self.call(
            id=id,
            terms={
                k: json.dumps(v)
                for k, v in terms.items()
            },
            timeout=timeout
        )

        if resp.text: return resp.text

        return json.loads(resp.object)

    def request_definitions(self, chunk, timeout=300):

        defs = self.request(
            id="extract-definitions",
            terms={
                "text": chunk
            },
            timeout=timeout
        )

        return [
            Definition(name=d["entity"], definition=d["definition"])
            for d in defs
        ]

    def request_relationships(self, chunk, timeout=300):

        return self.call(
            id="extract-relationships",
            terms={
                "text": chunk
            },
            timeout=timeout
        )

    def request_topics(self, chunk, timeout=300):

        return self.call(
            id="extract-topics",
            terms={
                "text": chunk
            },
            timeout=timeout
        )

    def request_rows(self, schema, chunk, timeout=300):

        return self.call(
            id="extract-rows",
            terms={
                "chunk": chunk,
                "row-schema": {
                    "name": schema.name,
                    "description": schema.description,
                    "fields": [
                        {
                            "name": f.name, "type": str(f.type),
                            "size": f.size, "primary": f.primary,
                            "description": f.description,
                        }
                        for f in schema.fields
                    ]
                }
            },
            timeout=timeout
        )

    def request_kg_prompt(self, query, kg, timeout=300):

        return self.call(
            id="kg-prompt",
            terms={
                "query": query,
                "kg": [
                    { "s": v[0], "p": v[1], "o": v[2] }
                    for v in kg
                ]
            },
            timeout=timeout
        )

    def request_document_prompt(self, query, documents, timeout=300):

        return self.call(
            id="document-prompt",
            terms={
                "query": query,
                "documents": documents,
            },
            timeout=timeout
        )


