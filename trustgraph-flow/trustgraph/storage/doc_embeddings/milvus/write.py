
"""
Accepts entity/vector pairs and writes them to a Milvus store.
"""

from .... direct.milvus_doc_embeddings import DocVectors

from .... schema import DocumentEmbeddings
from .... schema import document_embeddings_store_queue
from .... log_level import LogLevel
from .... base import Consumer

module = "de-write"

default_input_queue = document_embeddings_store_queue
default_subscriber = module
default_store_uri = 'http://localhost:19530'

class Processor(Consumer):

    def __init__(self, **params):

        input_queue = params.get("input_queue", default_input_queue)
        subscriber = params.get("subscriber", default_subscriber)
        store_uri = params.get("store_uri", default_store_uri)

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "subscriber": subscriber,
                "input_schema": DocumentEmbeddings,
                "store_uri": store_uri,
            }
        )

        self.vecstore = DocVectors(store_uri)

    async def handle(self, msg):

        v = msg.value()

        for emb in v.chunks:

            chunk = emb.chunk.decode("utf-8")
            if chunk == "" or chunk is None: continue

            for vec in emb.vectors:

                if chunk != "" and v.chunk is not None:
                    for vec in v.vectors:
                        self.vecstore.insert(vec, chunk)

    @staticmethod
    def add_args(parser):

        Consumer.add_args(
            parser, default_input_queue, default_subscriber,
        )

        parser.add_argument(
            '-t', '--store-uri',
            default=default_store_uri,
            help=f'Milvus store URI (default: {default_store_uri})'
        )

def run():

    Processor.launch(module, __doc__)

