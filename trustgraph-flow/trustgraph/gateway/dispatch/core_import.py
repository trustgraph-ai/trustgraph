
import asyncio
import json
import uuid
import msgpack
from . knowledge import KnowledgeRequestor

class CoreImport:

    def __init__(self, pulsar_client):
        self.pulsar_client = pulsar_client

    async def process(self, data, error, ok, params):

        id = params["id"]
        user = params["user"]

        kr = KnowledgeRequestor(
            pulsar_client = self.pulsar_client,
            consumer = "api-gateway-core-import-" + str(uuid.uuid4()),
            subscriber = "api-gateway-core-import-" + str(uuid.uuid4()),
        )

        await kr.start()

        try:

            unpacker = msgpack.Unpacker()

            while True:
                buf = await data.read(128*1024)
                if not buf: break

                unpacker.feed(buf)

                for unpacked in unpacker:

                    if unpacked[0] == "t":
                        msg = unpacked[1]
                        msg = {
                            "operation": "put-kg-core",
                            "user": user,
                            "id": id,
                            "triples": {
                                "metadata": {
                                    "id": id,
                                    "metadata": msg["m"]["m"],
                                    "user": user,
                                    "collection": "default", # Not used?
                                },
                                "triples": msg["t"],
                            }
                        }

                        await kr.process(msg)
                        
                    elif unpacked[0] == "ge":
                        msg = unpacked[1]
                        msg = {
                            "operation": "put-kg-core",
                            "user": user,
                            "id": id,
                            "graph-embeddings": {
                                "metadata": {
                                    "id": id,
                                    "metadata": msg["m"]["m"],
                                    "user": user,
                                    "collection": "default", # Not used?
                                },
                                "entities": [
                                    {
                                        "entity": ent["e"],
                                        "vectors": ent["v"],
                                    }
                                    for ent in msg["e"]
                                ]
                            }
                        }

                        await kr.process(msg)

        except Exception as e:
            print("Exception:", e)
            await error(str(e))

        finally:

            await kr.stop()

        print("All done.")
        response = await ok()
        await response.write_eof()

        return response
