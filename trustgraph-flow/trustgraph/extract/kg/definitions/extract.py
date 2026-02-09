
"""
Simple decoder, accepts text chunks input, applies entity analysis to
get entity definitions which are output as graph edges along with
entity/context definitions for embedding.
"""

import json
import urllib.parse
import logging

from .... schema import Chunk, Triple, Triples, Metadata, Value

# Module logger
logger = logging.getLogger(__name__)
from .... schema import EntityContext, EntityContexts
from .... schema import PromptRequest, PromptResponse
from .... rdf import TRUSTGRAPH_ENTITIES, DEFINITION, RDF_LABEL, SUBJECT_OF

from .... base import FlowProcessor, ConsumerSpec,  ProducerSpec
from .... base import PromptClientSpec

DEFINITION_VALUE = Value(value=DEFINITION, is_uri=True)
RDF_LABEL_VALUE = Value(value=RDF_LABEL, is_uri=True)
SUBJECT_OF_VALUE = Value(value=SUBJECT_OF, is_uri=True)

default_ident = "kg-extract-definitions"
default_concurrency = 1

class Processor(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")
        concurrency = params.get("concurrency", 1)

        super(Processor, self).__init__(
            **params | {
                "id": id,
                "concurrency": concurrency,
            }
        )

        self.register_specification(
            ConsumerSpec(
                name = "input",
                schema = Chunk,
                handler = self.on_message,
                concurrency = concurrency,
            )
        )

        self.register_specification(
            PromptClientSpec(
                request_name = "prompt-request",
                response_name = "prompt-response",
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

        v = msg.value()
        logger.info(f"Extracting definitions from {v.metadata.id}...")

        chunk = v.chunk.decode("utf-8")

        logger.debug(f"Processing chunk: {chunk[:200]}...")  # Log first 200 chars

        try:

            try:

                defs = await flow("prompt-request").extract_definitions(
                    text = chunk
                )

                logger.debug(f"Definitions response: {defs}")

                if type(defs) != list:
                    raise RuntimeError("Expecting array in prompt response")

            except Exception as e:
                logger.error(f"Prompt exception: {e}", exc_info=True)
                raise e

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

                # Output entity name as context for direct name matching
                entities.append(EntityContext(
                    entity=s_value,
                    context=s,
                ))

                # Output definition as context for semantic matching
                entities.append(EntityContext(
                    entity=s_value,
                    context=defn["definition"],
                ))

            if triples:
                await self.emit_triples(
                    flow("triples"),
                    Metadata(
                        id=v.metadata.id,
                        metadata=[],
                        user=v.metadata.user,
                        collection=v.metadata.collection,
                    ),
                    triples
                )

            if entities:
                await self.emit_ecs(
                    flow("entity-contexts"),
                    Metadata(
                        id=v.metadata.id,
                        metadata=[],
                        user=v.metadata.user,
                        collection=v.metadata.collection,
                    ),
                    entities
                )

        except Exception as e:
            logger.error(f"Definitions extraction exception: {e}", exc_info=True)

        logger.debug("Definitions extraction complete")

    @staticmethod
    def add_args(parser):

        parser.add_argument(
            '-c', '--concurrency',
            type=int,
            default=default_concurrency,
            help=f'Concurrent processing threads (default: {default_concurrency})'
        )

        FlowProcessor.add_args(parser)

def run():

    Processor.launch(default_ident, __doc__)

