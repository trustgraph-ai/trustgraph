
import asyncio
import json
import uuid
import msgpack
from . knowledge import KnowledgeRequestor

class CoreExport:

    def __init__(self, pulsar_client):
        self.pulsar_client = pulsar_client
        
    async def process(self, data, error, ok, params):

        id = params["id"]
        user = params["user"]

        response = await ok()

        kr = KnowledgeRequestor(
            pulsar_client = self.pulsar_client,
            consumer = "api-gateway-core-export-" + str(uuid.uuid4()),
            subscriber = "api-gateway-core-export-" + str(uuid.uuid4()),
        )

        try:

            await kr.start()

            async def responder(resp, fin):

                if "graph-embeddings" in resp:

                    data = resp["graph-embeddings"]

                    msg = (
                        "ge",
                        {
                            "m": {
                                "i": data["metadata"]["id"], 
                                "m": data["metadata"]["metadata"],
                                "u": data["metadata"]["user"],
                                "c": data["metadata"]["collection"],
                            },
                            "e": [
                                {
                                    "e": ent["entity"],
                                    "v": ent["vectors"],
                                }
                                for ent in data["entities"]
                            ]
                        }
                    )

                    enc = msgpack.packb(msg)
                    await response.write(enc)

                if "triples" in resp:

                    data = resp["triples"]
                    msg = (
                        "t",
                        {
                            "m": {
                                "i": data["metadata"]["id"], 
                                "m": data["metadata"]["metadata"],
                                "u": data["metadata"]["user"],
                                "c": data["metadata"]["collection"],
                            },
                            "t": data["triples"],
                        }
                    )

                    enc = msgpack.packb(msg)
                    await response.write(enc)

            await kr.process(
                {
                    "operation": "get-kg-core",
                    "user": user,
                    "id": id,
                },
                responder
            )

        except Exception as e:

            print("Exception:", e)

        finally:

            await kr.stop()

        await response.write_eof()

        return response

