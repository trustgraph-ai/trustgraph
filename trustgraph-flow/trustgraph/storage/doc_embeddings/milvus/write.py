
"""
Accepts entity/vector pairs and writes them to a Milvus store.
"""

from .... direct.milvus_doc_embeddings import DocVectors
from .... base import DocumentEmbeddingsStoreService

default_ident = "de-write"
default_store_uri = 'http://localhost:19530'

class Processor(DocumentEmbeddingsStoreService):

    def __init__(self, **params):

        store_uri = params.get("store_uri", default_store_uri)

        super(Processor, self).__init__(
            **params | {
                "store_uri": store_uri,
            }
        )

        self.vecstore = DocVectors(store_uri)

    async def store_document_embeddings(self, message):

        for emb in message.chunks:

            if emb.chunk is None or emb.chunk == b"": continue
            
            chunk = emb.chunk.decode("utf-8")
            if chunk == "": continue

            for vec in emb.vectors:
                self.vecstore.insert(
                    vec, chunk, 
                    message.metadata.user, 
                    message.metadata.collection
                )

    @staticmethod
    def add_args(parser):

        DocumentEmbeddingsStoreService.add_args(parser)

        parser.add_argument(
            '-t', '--store-uri',
            default=default_store_uri,
            help=f'Milvus store URI (default: {default_store_uri})'
        )

def run():

    Processor.launch(default_ident, __doc__)

