
import asyncio
import uuid
from aiohttp import WSMsgType

from .. schema import Metadata
from .. schema import DocumentEmbeddings, ChunkEmbeddings
from .. schema import document_embeddings_store_queue
from .. base import Publisher

from . socket import SocketEndpoint
from . serialize import to_subgraph

class DocumentEmbeddingsLoadEndpoint(SocketEndpoint):

    def __init__(
            self, pulsar_client, auth, path="/api/v1/load/document-embeddings",
    ):

        super(DocumentEmbeddingsLoadEndpoint, self).__init__(
            endpoint_path=path, auth=auth,
        )

        self.pulsar_client=pulsar_client

        self.publisher = Publisher(
            self.pulsar_client, document_embeddings_store_queue,
            schema=DocumentEmbeddings
        )

    async def start(self):

        await self.publisher.start()

    async def listener(self, ws, running):
        
        async for msg in ws:
            # On error, finish
            if msg.type == WSMsgType.ERROR:
                break
            else:

                data = msg.json()

                elt = DocumentEmbeddings(
                    metadata=Metadata(
                        id=data["metadata"]["id"],
                        metadata=to_subgraph(data["metadata"]["metadata"]),
                        user=data["metadata"]["user"],
                        collection=data["metadata"]["collection"],
                    ),
                    chunks=[
                        ChunkEmbeddings(
                            chunk=de["chunk"].encode("utf-8"),
                            vectors=de["vectors"],
                        )
                        for de in data["chunks"]
                    ],
                )

                await self.publisher.send(None, elt)

        running.stop()
