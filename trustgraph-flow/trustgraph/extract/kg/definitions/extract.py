
"""
Simple decoder, accepts text chunks input, applies entity analysis to
get entity definitions which are output as graph edges along with
entity/context definitions for embedding.
"""

import json
import asyncio
import urllib.parse
from pulsar.schema import JsonSchema
import uuid

from .... schema import Chunk, Triple, Triples, Metadata, Value
from .... schema import EntityContext, EntityContexts
from .... schema import PromptRequest, PromptResponse
from .... log_level import LogLevel
from .... clients.prompt_client import PromptClient
from .... rdf import TRUSTGRAPH_ENTITIES, DEFINITION, RDF_LABEL, SUBJECT_OF

from .... base import FlowProcessor, SubscriberSpec, ConsumerSpec
from .... base import ProducerSpec

DEFINITION_VALUE = Value(value=DEFINITION, is_uri=True)
RDF_LABEL_VALUE = Value(value=RDF_LABEL, is_uri=True)
SUBJECT_OF_VALUE = Value(value=SUBJECT_OF, is_uri=True)

default_ident = "kg-extract-definitions"

class Processor(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")

        super(Processor, self).__init__(
            **params | {
                "id": id,
            }
        )

        self.register_specification(
            ConsumerSpec(
                name = "input",
                schema = Chunk,
                handler = self.on_message
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "prompt-request",
                schema = PromptRequest
            )
        )

        self.register_specification(
            SubscriberSpec(
                name = "prompt-response",
                schema = PromptResponse,
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "triples",
                schema = Triples
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "entity-contexts",
                schema = EntityContexts
            )
        )

    def to_uri(self, text):

        part = text.replace(" ", "-").lower().encode("utf-8")
        quoted = urllib.parse.quote(part)
        uri = TRUSTGRAPH_ENTITIES + quoted

        return uri

    def get_definitions(self, chunk):

        return self.prompt.request_definitions(chunk)

    async def emit_triples(self, pub, metadata, triples):

        t = Triples(
            metadata=metadata,
            triples=triples,
        )
        await pub.send(t)

    async def emit_ecs(self, pub, metadata, entities):

        t = EntityContexts(
            metadata=metadata,
            entities=entities,
        )
        await pub.send(t)

    async def on_message(self, msg, consumer, flow):

        id = str(uuid.uuid4())

        v = msg.value()
        print(f"Indexing {v.metadata.id}...", flush=True)

        chunk = v.chunk.decode("utf-8")

        print(chunk, flush=True)

        try:

            q = await flow.consumer["prompt-response"].subscribe(id)

            try:

                await flow.producer["prompt-request"].send(
                    PromptRequest(
                        id="extract-definitions",
                        terms={
                            "text": json.dumps(chunk)
                        },
                    ),
                    properties={"id": id}
                )

                # FIXME: hard-coded?
                resp = await asyncio.wait_for(
                    q.get(),
                    timeout=600
                )

                print("Response", resp, flush=True)

                if resp.error is not None:
                    print("Error:", resp.error.message, flush=True)
                    raise RuntimeError(resp.error.message)

                if resp.object is None:
                    raise RuntimeError("Expecting object in prompt response")

                defs = json.loads(resp.object)

            except Exception as e:
                print("Prompt exception:", e, flush=True)
                raise e
            finally:
                await flow.consumer["prompt-response"].unsubscribe(id)

            triples = []
            entities = []

            # FIXME: Putting metadata into triples store is duplicated in
            # relationships extractor too
            for t in v.metadata.metadata:
                triples.append(t)

            for defn in defs:

                s = defn["entity"]
                o = defn["definition"]

                if s == "": continue
                if o == "": continue

                if s is None: continue
                if o is None: continue

                s_uri = self.to_uri(s)

                s_value = Value(value=str(s_uri), is_uri=True)
                o_value = Value(value=str(o), is_uri=False)

                triples.append(Triple(
                    s=s_value,
                    p=RDF_LABEL_VALUE,
                    o=Value(value=s, is_uri=False),
                ))

                triples.append(Triple(
                    s=s_value, p=DEFINITION_VALUE, o=o_value
                ))

                triples.append(Triple(
                    s=s_value,
                    p=SUBJECT_OF_VALUE,
                    o=Value(value=v.metadata.id, is_uri=True)
                ))

                ec = EntityContext(
                    entity=s_value,
                    context=defn["definition"],
                )

                entities.append(ec)

            await self.emit_triples(
                flow.producer["triples"],
                Metadata(
                    id=v.metadata.id,
                    metadata=[],
                    user=v.metadata.user,
                    collection=v.metadata.collection,
                ),
                triples
            )

            await self.emit_ecs(
                flow.producer["entity-contexts"],
                Metadata(
                    id=v.metadata.id,
                    metadata=[],
                    user=v.metadata.user,
                    collection=v.metadata.collection,
                ),
                entities
            )

        except Exception as e:
            print("Exception: ", e, flush=True)

        print("Done.", flush=True)

    @staticmethod
    def add_args(parser):

        FlowProcessor.add_args(parser)

def run():

    Processor.launch(default_ident, __doc__)

