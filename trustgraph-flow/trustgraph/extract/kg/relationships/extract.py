
"""
Simple decoder, accepts text chunks input, applies entity
relationship analysis to get entity relationship edges which are output as
graph edges.
"""

import json
import urllib.parse

from .... schema import Chunk, Triple, Triples
from .... schema import Metadata, Value
from .... schema import PromptRequest, PromptResponse
from .... rdf import RDF_LABEL, TRUSTGRAPH_ENTITIES, SUBJECT_OF

from .... base import FlowProcessor, ConsumerSpec,  ProducerSpec
from .... base import PromptClientSpec

RDF_LABEL_VALUE = Value(value=RDF_LABEL, is_uri=True)
SUBJECT_OF_VALUE = Value(value=SUBJECT_OF, is_uri=True)

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
        print(f"Indexing {v.metadata.id}...", flush=True)

        chunk = v.chunk.decode("utf-8")

        print(chunk, flush=True)

        try:

            try:

                rels = await flow("prompt-request").extract_relationships(
                    text = chunk
                )

                print("Response", rels, flush=True)

                if type(rels) != list:
                    raise RuntimeError("Expecting array in prompt response")

            except Exception as e:
                print("Prompt exception:", e, flush=True)
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
                s_value = Value(value=str(s_uri), is_uri=True)

                p_uri = self.to_uri(p)
                p_value = Value(value=str(p_uri), is_uri=True)

                if rel["object-entity"]: 
                    o_uri = self.to_uri(o)
                    o_value = Value(value=str(o_uri), is_uri=True)
                else:
                    o_value = Value(value=str(o), is_uri=False)

                triples.append(Triple(
                    s=s_value,
                    p=p_value,
                    o=o_value
                ))

                # Label for s
                triples.append(Triple(
                    s=s_value,
                    p=RDF_LABEL_VALUE,
                    o=Value(value=str(s), is_uri=False)
                ))

                # Label for p
                triples.append(Triple(
                    s=p_value,
                    p=RDF_LABEL_VALUE,
                    o=Value(value=str(p), is_uri=False)
                ))

                if rel["object-entity"]:
                    # Label for o
                    triples.append(Triple(
                        s=o_value,
                        p=RDF_LABEL_VALUE,
                        o=Value(value=str(o), is_uri=False)
                    ))

                # 'Subject of' for s
                triples.append(Triple(
                    s=s_value,
                    p=SUBJECT_OF_VALUE,
                    o=Value(value=v.metadata.id, is_uri=True)
                ))

                if rel["object-entity"]:
                    # 'Subject of' for o
                    triples.append(Triple(
                        s=o_value,
                        p=SUBJECT_OF_VALUE,
                        o=Value(value=v.metadata.id, is_uri=True)
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
            print("Exception: ", e, flush=True)

        print("Done.", flush=True)

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

