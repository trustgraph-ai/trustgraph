
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

@dataclasses.dataclass
class Relationship:
    s: str
    p: str
    o: str
    o_entity: str

@dataclasses.dataclass
class Topic:
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

    def request(self, id, variables, timeout=300):

        resp = self.call(
            id=id,
            terms={
                k: json.dumps(v)
                for k, v in variables.items()
            },
            timeout=timeout
        )

        if resp.text: return resp.text

        return json.loads(resp.object)

    def request_definitions(self, chunk, timeout=300):

        defs = self.request(
            id="extract-definitions",
            variables={
                "text": chunk
            },
            timeout=timeout
        )

        return [
            Definition(name=d["entity"], definition=d["definition"])
            for d in defs
        ]

    def request_relationships(self, chunk, timeout=300):

        rels = self.request(
            id="extract-relationships",
            variables={
                "text": chunk
            },
            timeout=timeout
        )

        return [
            Relationship(
                s=d["subject"],
                p=d["predicate"],
                o=d["object"],
                o_entity=d["object-entity"]
            )
            for d in rels
        ]

    def request_topics(self, chunk, timeout=300):

        topics = self.request(
            id="extract-topics",
            variables={
                "text": chunk
            },
            timeout=timeout
        )
        
        return [
            Topic(name=d["topic"], definition=d["definition"])
            for d in topics
        ]

    def request_rows(self, schema, chunk, timeout=300):

        return self.request(
            id="extract-rows",
            variables={
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

        return self.request(
            id="kg-prompt",
            variables={
                "query": query,
                "knowledge": [
                    { "s": v[0], "p": v[1], "o": v[2] }
                    for v in kg
                ]
            },
            timeout=timeout
        )

    def request_document_prompt(self, query, documents, timeout=300):

        return self.request(
            id="document-prompt",
            variables={
                "query": query,
                "documents": documents,
            },
            timeout=timeout
        )


