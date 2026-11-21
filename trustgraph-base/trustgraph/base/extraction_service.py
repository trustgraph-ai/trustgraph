"""
Base extraction service supporting both flow mode (Chunk consumer)
and request/response mode (ExtractionRequest consumer).  Subclasses
implement do_extract() with extraction-specific logic.
"""

import logging
import time
import urllib.parse

from .flow_processor import FlowProcessor
from .consumer_spec import ConsumerSpec
from .producer_spec import ProducerSpec
from .parameter_spec import ParameterSpec
from .librarian_spec import LibrarianSpec
from .prompt_client import PromptClientSpec

from .. schema import (
    Chunk, Triples, Metadata, Triple,
    EntityContexts, EntityContext,
    ExtractionRequest, ExtractionResponse, Error,
)

from .. provenance import (
    subgraph_uri, subgraph_provenance_triples, set_graph, GRAPH_SOURCE,
)
from .. rdf import TRUSTGRAPH_ENTITIES

logger = logging.getLogger(__name__)


class ExtractionServiceBase(FlowProcessor):

    def __init__(self, **params):

        concurrency = params.get("concurrency", 1)
        self.triples_batch_size = params.get("triples_batch_size", 50)
        self.entity_batch_size = params.get("entity_batch_size", 5)
        self.component_version = params.get("component_version", "unknown")

        super(ExtractionServiceBase, self).__init__(**params)

        self.register_specification(
            ConsumerSpec(
                name="input",
                schema=Chunk,
                handler=self.on_message,
                concurrency=concurrency,
            )
        )

        self.register_specification(
            PromptClientSpec(
                request_name="prompt-request",
                response_name="prompt-response",
            )
        )

        self.register_specification(
            ProducerSpec(
                name="triples",
                schema=Triples
            )
        )

        self.register_specification(
            ProducerSpec(
                name="entity-contexts",
                schema=EntityContexts
            )
        )

        self.register_specification(ParameterSpec("llm-model"))
        self.register_specification(ParameterSpec("ontology"))

        self.register_specification(
            LibrarianSpec()
        )

        self.register_specification(
            ConsumerSpec(
                name="request",
                schema=ExtractionRequest,
                handler=self.on_extract_request,
            )
        )

        self.register_specification(
            ProducerSpec(
                name="response",
                schema=ExtractionResponse,
            )
        )

    def to_uri(self, text):
        part = text.replace(" ", "-").lower().encode("utf-8")
        quoted = urllib.parse.quote(part)
        return TRUSTGRAPH_ENTITIES + quoted

    def _on_extraction_complete(
        self, content_triples, entity_contexts, extracted_triples, duration,
    ):
        """Override for metrics or other post-processing."""
        pass

    async def do_extract(self, text, chunk_doc_id, flow):
        """
        Subclass implements extraction logic.

        Returns (content_triples, entity_contexts, extracted_triples).
        - content_triples: all graph triples including labels
        - entity_contexts: entity contexts for embedding (may be empty)
        - extracted_triples: subset of content_triples that are the actual
          extracted facts (used for provenance generation)
        """
        raise NotImplementedError

    def _generate_provenance(self, extracted_triples, chunk_uri, flow):

        if not extracted_triples:
            return []

        llm_model = flow("llm-model")
        ontology_uri = flow("ontology")

        sg_uri = subgraph_uri()
        prov_triples = subgraph_provenance_triples(
            subgraph_uri=sg_uri,
            extracted_triples=extracted_triples,
            chunk_uri=chunk_uri,
            component_name=self.id,
            component_version=self.component_version,
            llm_model=llm_model,
            ontology_uri=ontology_uri,
        )

        return list(set_graph(prov_triples, GRAPH_SOURCE))

    async def on_message(self, msg, consumer, flow):

        v = msg.value()
        logger.info(f"Extracting from {v.metadata.id}...")

        text = v.chunk.decode("utf-8")
        chunk_doc_id = v.document_id if v.document_id else v.metadata.id
        chunk_uri = v.metadata.id

        t0 = time.monotonic()

        try:

            content_triples, entity_contexts, extracted_triples = \
                await self.do_extract(text, chunk_doc_id, flow)

            prov_triples = self._generate_provenance(
                extracted_triples, chunk_uri, flow,
            )

            all_triples = content_triples + prov_triples

            for i in range(0, len(all_triples), self.triples_batch_size):
                batch = all_triples[i:i + self.triples_batch_size]
                await flow("triples").send(
                    Triples(
                        metadata=Metadata(
                            id=v.metadata.id,
                            root=v.metadata.root,
                            collection=v.metadata.collection,
                        ),
                        triples=batch,
                    )
                )

            for i in range(0, len(entity_contexts), self.entity_batch_size):
                batch = entity_contexts[i:i + self.entity_batch_size]
                await flow("entity-contexts").send(
                    EntityContexts(
                        metadata=Metadata(
                            id=v.metadata.id,
                            root=v.metadata.root,
                            collection=v.metadata.collection,
                        ),
                        entities=batch,
                    )
                )

            dur = time.monotonic() - t0

            self._on_extraction_complete(
                content_triples, entity_contexts,
                extracted_triples, dur,
            )

            logger.info(
                f"Extracted {len(content_triples)} triples, "
                f"{len(entity_contexts)} entities, "
                f"{len(prov_triples)} provenance triples "
                f"in {dur:.2f}s"
            )

        except Exception as e:
            logger.error(f"Extraction exception: {e}", exc_info=True)

    async def on_extract_request(self, msg, consumer, flow):

        id = msg.properties()["id"]

        try:

            v = msg.value()
            text = v.text
            document_id = v.document_id

            if not text and document_id:
                text = await flow.librarian.fetch_document_text(
                    document_id=document_id,
                )

            if not text:
                raise RuntimeError("No text provided and no document_id")

            logger.info(
                f"Extraction request {id}: "
                f"{len(text)} chars, doc={document_id}"
            )

            content_triples, entity_contexts, extracted_triples = \
                await self.do_extract(text, document_id, flow)

            prov_triples = self._generate_provenance(
                extracted_triples, document_id, flow,
            )

            await flow("response").send(
                ExtractionResponse(
                    kind="triples",
                    triples=content_triples,
                ),
                properties={"id": id},
            )

            if entity_contexts:
                await flow("response").send(
                    ExtractionResponse(
                        kind="entity-contexts",
                        entity_contexts=entity_contexts,
                    ),
                    properties={"id": id},
                )

            await flow("response").send(
                ExtractionResponse(
                    kind="provenance",
                    triples=prov_triples,
                    end_of_stream=True,
                ),
                properties={"id": id},
            )

            logger.info(f"Extraction request {id}: complete")

        except Exception as e:

            logger.error(
                f"Extraction request {id} failed: "
                f"{type(e).__name__}: {e}",
                exc_info=True,
            )

            await flow("response").send(
                ExtractionResponse(
                    error=Error(
                        type="extraction-error",
                        message=str(e),
                    ),
                    end_of_stream=True,
                ),
                properties={"id": id},
            )

    @staticmethod
    def add_args(parser):

        parser.add_argument(
            '--triples-batch-size',
            type=int,
            default=50,
            help='Maximum triples per output message (default: 50)'
        )

        parser.add_argument(
            '--entity-batch-size',
            type=int,
            default=5,
            help='Maximum entity contexts per output message (default: 5)'
        )

        FlowProcessor.add_args(parser)
