
import asyncio
from pulsar.schema import JsonSchema
import uuid
from aiohttp import WSMsgType

from .. schema import Metadata
from .. schema import Triples
from .. schema import triples_store_queue
from .. base import Publisher

from . socket import SocketEndpoint
from . serialize import to_subgraph

class TriplesLoadEndpoint(SocketEndpoint):

    def __init__(self, pulsar_client, auth, path="/api/v1/load/triples"):

        super(TriplesLoadEndpoint, self).__init__(
            endpoint_path=path, auth=auth,
        )

        self.pulsar_client=pulsar_client

        self.publisher = Publisher(
            self.pulsar_client, triples_store_queue,
            schema=JsonSchema(Triples)
        )

    async def start(self):

        self.publisher.start()

    async def listener(self, ws, running):
        
        async for msg in ws:
            # On error, finish
            if msg.type == WSMsgType.ERROR:
                break
            else:

                data = msg.json()

                elt = Triples(
                    metadata=Metadata(
                        id=data["metadata"]["id"],
                        metadata=to_subgraph(data["metadata"]["metadata"]),
                        user=data["metadata"]["user"],
                        collection=data["metadata"]["collection"],
                    ),
                    triples=to_subgraph(data["triples"]),
                )

                await self.publisher.send(None, elt)


        running.stop()
