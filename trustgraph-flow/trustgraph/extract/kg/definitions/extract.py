
"""
Simple decoder, accepts text chunks input, applies entity analysis to
get entity definitions which are output as graph edges along with
entity/context definitions for embedding.
"""

import logging

from .. extract_metrics import (
    extraction_duration_metric, extraction_triple_metric,
    extraction_entity_metric, extraction_empty_metric,
)

from .... schema import Triple, Term, IRI, LITERAL
from .... schema import EntityContext
from .... rdf import DEFINITION, RDF_LABEL

from .... base import ExtractionServiceBase

from .... flow_version import __version__ as COMPONENT_VERSION

DEFINITION_VALUE = Term(type=IRI, iri=DEFINITION)
RDF_LABEL_VALUE = Term(type=IRI, iri=RDF_LABEL)
default_ident = "kg-extract-definitions"

logger = logging.getLogger(__name__)


class Processor(ExtractionServiceBase):

    def __init__(self, **params):

        super(Processor, self).__init__(
            **params | {
                "component_version": COMPONENT_VERSION,
            }
        )

    async def do_extract(self, text, chunk_doc_id, flow):

        logger.debug(f"Processing chunk: {text[:200]}...")

        try:

            result = await flow("prompt-request").extract_definitions(
                text=text
            )

            defs = result.objects
            logger.debug(f"Definitions response: {defs}")

            if type(defs) != list:
                raise RuntimeError("Expecting array in prompt response")

        except Exception as e:
            logger.error(f"Prompt exception: {e}", exc_info=True)
            raise e

        triples = []
        extracted_triples = []
        entities = []

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

            definition_triple = Triple(
                s=s_value, p=DEFINITION_VALUE, o=o_value
            )
            triples.append(definition_triple)
            extracted_triples.append(definition_triple)

            entities.append(EntityContext(
                entity=s_value,
                context=s,
                chunk_id=chunk_doc_id,
            ))

            entities.append(EntityContext(
                entity=s_value,
                context=defn["definition"],
                chunk_id=chunk_doc_id,
            ))

        return triples, entities, extracted_triples

    def _on_extraction_complete(
        self, content_triples, entity_contexts, extracted_triples, duration,
    ):
        labels = dict(processor=self.id, extractor="definitions")
        extraction_duration_metric.labels(**labels).observe(duration)
        extraction_triple_metric.labels(**labels).inc(len(extracted_triples))
        extraction_entity_metric.labels(**labels).inc(len(entity_contexts))
        if not extracted_triples:
            extraction_empty_metric.labels(**labels).inc()

    @staticmethod
    def add_args(parser):
        ExtractionServiceBase.add_args(parser)

def run():

    Processor.launch(default_ident, __doc__)
