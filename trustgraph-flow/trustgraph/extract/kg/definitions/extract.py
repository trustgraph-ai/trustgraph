
"""
Simple decoder, accepts text chunks input, applies entity analysis to
get entity definitions which are output as graph edges along with
entity/context definitions for embedding.
"""

import urllib.parse
from pulsar.schema import JsonSchema

from .... schema import Chunk, Triple, Triples, Metadata, Value
from .... schema import EntityContext, EntityContexts
from .... schema import chunk_ingest_queue, triples_store_queue
from .... schema import entity_contexts_ingest_queue
from .... schema import prompt_request_queue
from .... schema import prompt_response_queue
from .... log_level import LogLevel
from .... clients.prompt_client import PromptClient
from .... rdf import TRUSTGRAPH_ENTITIES, DEFINITION, RDF_LABEL, SUBJECT_OF
from .... base import ConsumerProducer

DEFINITION_VALUE = Value(value=DEFINITION, is_uri=True)
RDF_LABEL_VALUE = Value(value=RDF_LABEL, is_uri=True)
SUBJECT_OF_VALUE = Value(value=SUBJECT_OF, is_uri=True)

module = "kg-extract-definitions"

default_input_queue = chunk_ingest_queue
default_output_queue = triples_store_queue
default_entity_context_queue = entity_contexts_ingest_queue
default_subscriber = module

class Processor(ConsumerProducer):

    def __init__(self, **params):

        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        ec_queue = params.get(
            "entity_context_queue",
            default_entity_context_queue
        )
        subscriber = params.get("subscriber", default_subscriber)
        pr_request_queue = params.get(
            "prompt_request_queue", prompt_request_queue
        )
        pr_response_queue = params.get(
            "prompt_response_queue", prompt_response_queue
        )

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "output_queue": output_queue,
                "subscriber": subscriber,
                "input_schema": Chunk,
                "output_schema": Triples,
                "prompt_request_queue": pr_request_queue,
                "prompt_response_queue": pr_response_queue,
            }
        )

        self.ec_prod = self.client.create_producer(
            topic=ec_queue,
            schema=JsonSchema(EntityContexts),
        )

        __class__.pubsub_metric.info({
            "input_queue": input_queue,
            "output_queue": output_queue,
            "entity_context_queue": ec_queue,
            "prompt_request_queue": pr_request_queue,
            "prompt_response_queue": pr_response_queue,
            "subscriber": subscriber,
            "input_schema": Chunk.__name__,
            "output_schema": Triples.__name__,
            "vector_schema": EntityContexts.__name__,
        })

        self.prompt = PromptClient(
            pulsar_host=self.pulsar_host,
            pulsar_api_key=self.pulsar_api_key,
            input_queue=pr_request_queue,
            output_queue=pr_response_queue,
            subscriber = module + "-prompt",
        )

    def to_uri(self, text):

        part = text.replace(" ", "-").lower().encode("utf-8")
        quoted = urllib.parse.quote(part)
        uri = TRUSTGRAPH_ENTITIES + quoted

        return uri

    def get_definitions(self, chunk):

        return self.prompt.request_definitions(chunk)

    async def emit_edges(self, metadata, triples):

        t = Triples(
            metadata=metadata,
            triples=triples,
        )
        await self.send(t)

    async def emit_ecs(self, metadata, entities):

        t = EntityContexts(
            metadata=metadata,
            entities=entities,
        )
        self.ec_prod.send(t)

    async def handle(self, msg):

        v = msg.value()
        print(f"Indexing {v.metadata.id}...", flush=True)

        chunk = v.chunk.decode("utf-8")

        try:

            defs = self.get_definitions(chunk)

            triples = []
            entities = []

            # FIXME: Putting metadata into triples store is duplicated in
            # relationships extractor too
            for t in v.metadata.metadata:
                triples.append(t)

            for defn in defs:

                s = defn.name
                o = defn.definition

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
                    context=defn.definition,
                )

                entities.append(ec)
                    

            await self.emit_edges(
                Metadata(
                    id=v.metadata.id,
                    metadata=[],
                    user=v.metadata.user,
                    collection=v.metadata.collection,
                ),
                triples
            )

            await self.emit_ecs(
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

        ConsumerProducer.add_args(
            parser, default_input_queue, default_subscriber,
            default_output_queue,
        )

        parser.add_argument(
            '-e', '--entity-context-queue',
            default=default_entity_context_queue,
            help=f'Entity context queue (default: {default_entity_context_queue})'
        )

        parser.add_argument(
            '--prompt-request-queue',
            default=prompt_request_queue,
            help=f'Prompt request queue (default: {prompt_request_queue})',
        )

        parser.add_argument(
            '--prompt-completion-response-queue',
            default=prompt_response_queue,
            help=f'Prompt response queue (default: {prompt_response_queue})',
        )

def run():

    Processor.launch(module, __doc__)

