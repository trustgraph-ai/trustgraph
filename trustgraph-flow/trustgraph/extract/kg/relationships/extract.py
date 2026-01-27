
"""
Simple decoder, accepts text chunks input, applies entity
relationship analysis to get entity relationship edges which are output as
graph edges.
"""

import json
import logging
import urllib.parse

# Module logger
logger = logging.getLogger(__name__)

from .... schema import Chunk, Triple, Triples
from .... schema import Metadata, Term, IRI, LITERAL
from .... schema import PromptRequest, PromptResponse
from .... rdf import RDF_LABEL, TRUSTGRAPH_ENTITIES, SUBJECT_OF

from .... base import FlowProcessor, ConsumerSpec,  ProducerSpec
from .... base import PromptClientSpec

RDF_LABEL_VALUE = Term(type=IRI, iri=RDF_LABEL)
SUBJECT_OF_VALUE = Term(type=IRI, iri=SUBJECT_OF)

default_ident = "kg-extract-relationships"
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

    async def on_message(self, msg, consumer, flow):

        v = msg.value()
        logger.info(f"Extracting relationships from {v.metadata.id}...")

        chunk = v.chunk.decode("utf-8")

        logger.debug(f"Processing chunk: {chunk[:100]}..." if len(chunk) > 100 else f"Processing chunk: {chunk}")

        try:

            try:

                rels = await flow("prompt-request").extract_relationships(
                    text = chunk
                )

                logger.debug(f"Prompt response: {rels}")

                if type(rels) != list:
                    raise RuntimeError("Expecting array in prompt response")

            except Exception as e:
                logger.error(f"Prompt exception: {e}", exc_info=True)
                raise e

            triples = []

            # FIXME: Putting metadata into triples store is duplicated in
            # relationships extractor too
            for t in v.metadata.metadata:
                triples.append(t)

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

                triples.append(Triple(
                    s=s_value,
                    p=p_value,
                    o=o_value
                ))

                # Label for s
                triples.append(Triple(
                    s=s_value,
                    p=RDF_LABEL_VALUE,
                    o=Term(type=LITERAL, value=str(s))
                ))

                # Label for p
                triples.append(Triple(
                    s=p_value,
                    p=RDF_LABEL_VALUE,
                    o=Term(type=LITERAL, value=str(p))
                ))

                if rel["object-entity"]:
                    # Label for o
                    triples.append(Triple(
                        s=o_value,
                        p=RDF_LABEL_VALUE,
                        o=Term(type=LITERAL, value=str(o))
                    ))

                # 'Subject of' for s
                triples.append(Triple(
                    s=s_value,
                    p=SUBJECT_OF_VALUE,
                    o=Term(type=IRI, iri=v.metadata.id)
                ))

                if rel["object-entity"]:
                    # 'Subject of' for o
                    triples.append(Triple(
                        s=o_value,
                        p=SUBJECT_OF_VALUE,
                        o=Term(type=IRI, iri=v.metadata.id)
                    ))

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

        except Exception as e:
            logger.error(f"Relationship extraction exception: {e}", exc_info=True)

        logger.debug("Relationship extraction complete")

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

