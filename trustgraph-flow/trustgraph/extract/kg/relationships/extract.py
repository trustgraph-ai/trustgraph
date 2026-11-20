
"""
Simple decoder, accepts text chunks input, applies entity
relationship analysis to get entity relationship edges which are output as
graph edges.
"""

import logging

from .. extract_metrics import (
    extraction_duration_metric, extraction_triple_metric,
    extraction_empty_metric,
)

from .... schema import Triple, Term, IRI, LITERAL
from .... rdf import RDF_LABEL

from .... base import ExtractionServiceBase

from .... flow_version import __version__ as COMPONENT_VERSION

RDF_LABEL_VALUE = Term(type=IRI, iri=RDF_LABEL)
default_ident = "kg-extract-relationships"

logger = logging.getLogger(__name__)


class Processor(ExtractionServiceBase):

    def __init__(self, **params):

        super(Processor, self).__init__(
            **params | {
                "component_version": COMPONENT_VERSION,
            }
        )

    async def do_extract(self, text, chunk_doc_id, flow):

        logger.debug(
            f"Processing chunk: {text[:100]}..."
            if len(text) > 100 else f"Processing chunk: {text}"
        )

        try:

            result = await flow("prompt-request").extract_relationships(
                text=text
            )

            rels = result.objects
            logger.debug(f"Prompt response: {rels}")

            if type(rels) != list:
                raise RuntimeError("Expecting array in prompt response")

        except Exception as e:
            logger.error(f"Prompt exception: {e}", exc_info=True)
            raise e

        triples = []
        extracted_triples = []

        for rel in rels:

            s = rel["subject"]
            p = rel["predicate"]
            o = rel["object"]

            if s == "": continue
            if p == "": continue
            if o == "": continue

            if s is None: continue
            if p is None: continue
            if o is None: continue

            s_uri = self.to_uri(s)
            s_value = Term(type=IRI, iri=str(s_uri))

            p_uri = self.to_uri(p)
            p_value = Term(type=IRI, iri=str(p_uri))

            if rel["object-entity"]:
                o_uri = self.to_uri(o)
                o_value = Term(type=IRI, iri=str(o_uri))
            else:
                o_value = Term(type=LITERAL, value=str(o))

            relationship_triple = Triple(
                s=s_value,
                p=p_value,
                o=o_value
            )
            triples.append(relationship_triple)
            extracted_triples.append(relationship_triple)

            triples.append(Triple(
                s=s_value,
                p=RDF_LABEL_VALUE,
                o=Term(type=LITERAL, value=str(s))
            ))

            triples.append(Triple(
                s=p_value,
                p=RDF_LABEL_VALUE,
                o=Term(type=LITERAL, value=str(p))
            ))

            if rel["object-entity"]:
                triples.append(Triple(
                    s=o_value,
                    p=RDF_LABEL_VALUE,
                    o=Term(type=LITERAL, value=str(o))
                ))

        return triples, [], extracted_triples

    def _on_extraction_complete(
        self, content_triples, entity_contexts, extracted_triples, duration,
    ):
        labels = dict(processor=self.id, extractor="relationships")
        extraction_duration_metric.labels(**labels).observe(duration)
        extraction_triple_metric.labels(**labels).inc(len(extracted_triples))
        if not extracted_triples:
            extraction_empty_metric.labels(**labels).inc()

    @staticmethod
    def add_args(parser):
        ExtractionServiceBase.add_args(parser)

def run():

    Processor.launch(default_ident, __doc__)
