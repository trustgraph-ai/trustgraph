
"""
Simple decoder, accepts text chunks input, applies entity analysis to
get entity definitions which are output as graph edges along with
entity/context definitions for embedding.
"""

import json
import urllib.parse
import logging

from .... schema import Chunk, Triple, Triples, Metadata, Term, IRI, LITERAL

# Module logger
logger = logging.getLogger(__name__)
from .... schema import EntityContext, EntityContexts
from .... schema import PromptRequest, PromptResponse
from .... rdf import TRUSTGRAPH_ENTITIES, DEFINITION, RDF_LABEL, SUBJECT_OF

from .... base import FlowProcessor, ConsumerSpec,  ProducerSpec
from .... base import PromptClientSpec, ParameterSpec

from .... provenance import statement_uri, triple_provenance_triples, set_graph, GRAPH_SOURCE
from .... flow_version import __version__ as COMPONENT_VERSION

DEFINITION_VALUE = Term(type=IRI, iri=DEFINITION)
RDF_LABEL_VALUE = Term(type=IRI, iri=RDF_LABEL)
SUBJECT_OF_VALUE = Term(type=IRI, iri=SUBJECT_OF)

default_ident = "kg-extract-definitions"
default_concurrency = 1
default_triples_batch_size = 50
default_entity_batch_size = 5

class Processor(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")
        concurrency = params.get("concurrency", 1)
        self.triples_batch_size = params.get("triples_batch_size", default_triples_batch_size)
        self.entity_batch_size = params.get("entity_batch_size", default_entity_batch_size)

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

        # Optional flow parameters for provenance
        self.register_specification(ParameterSpec("llm-model"))
        self.register_specification(ParameterSpec("ontology"))

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

            # Get chunk document ID for provenance linking
            chunk_doc_id = v.document_id if v.document_id else v.metadata.id
            chunk_uri = v.metadata.id  # The URI form for the chunk

            # Get optional provenance parameters
            llm_model = flow("llm-model")
            ontology_uri = flow("ontology")

            # Note: Document metadata is now emitted once by librarian at processing
            # initiation, so we don't need to duplicate it here.

            for defn in defs:

                s = defn["entity"]
                o = defn["definition"]

                if s == "": continue
                if o == "": continue

                if s is None: continue
                if o is None: continue

                s_uri = self.to_uri(s)

                s_value = Term(type=IRI, iri=str(s_uri))
                o_value = Term(type=LITERAL, value=str(o))

                triples.append(Triple(
                    s=s_value,
                    p=RDF_LABEL_VALUE,
                    o=Term(type=LITERAL, value=s),
                ))

                # The definition triple - this is the main extracted fact
                definition_triple = Triple(
                    s=s_value, p=DEFINITION_VALUE, o=o_value
                )
                triples.append(definition_triple)

                # Generate provenance for the definition triple (reification)
                # Provenance triples go in the source graph for separation from core knowledge
                stmt_uri = statement_uri()
                prov_triples = triple_provenance_triples(
                    stmt_uri=stmt_uri,
                    extracted_triple=definition_triple,
                    chunk_uri=chunk_uri,
                    component_name=default_ident,
                    component_version=COMPONENT_VERSION,
                    llm_model=llm_model,
                    ontology_uri=ontology_uri,
                )
                triples.extend(set_graph(prov_triples, GRAPH_SOURCE))

                # Link entity to chunk (not top-level document)
                triples.append(Triple(
                    s=s_value,
                    p=SUBJECT_OF_VALUE,
                    o=Term(type=IRI, iri=chunk_uri)
                ))

                # Output entity name as context for direct name matching
                # Include chunk_id for embedding provenance
                entities.append(EntityContext(
                    entity=s_value,
                    context=s,
                    chunk_id=chunk_doc_id,
                ))

                # Output definition as context for semantic matching
                # Include chunk_id for embedding provenance
                entities.append(EntityContext(
                    entity=s_value,
                    context=defn["definition"],
                    chunk_id=chunk_doc_id,
                ))

            # Send triples in batches
            for i in range(0, len(triples), self.triples_batch_size):
                batch = triples[i:i + self.triples_batch_size]
                await self.emit_triples(
                    flow("triples"),
                    Metadata(
                        id=v.metadata.id,
                        root=v.metadata.root,
                        user=v.metadata.user,
                        collection=v.metadata.collection,
                    ),
                    batch
                )

            # Send entity contexts in batches
            for i in range(0, len(entities), self.entity_batch_size):
                batch = entities[i:i + self.entity_batch_size]
                await self.emit_ecs(
                    flow("entity-contexts"),
                    Metadata(
                        id=v.metadata.id,
                        root=v.metadata.root,
                        user=v.metadata.user,
                        collection=v.metadata.collection,
                    ),
                    batch
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

        parser.add_argument(
            '--triples-batch-size',
            type=int,
            default=default_triples_batch_size,
            help=f'Maximum triples per output message (default: {default_triples_batch_size})'
        )

        parser.add_argument(
            '--entity-batch-size',
            type=int,
            default=default_entity_batch_size,
            help=f'Maximum entity contexts per output message (default: {default_entity_batch_size})'
        )

        FlowProcessor.add_args(parser)

def run():

    Processor.launch(default_ident, __doc__)

