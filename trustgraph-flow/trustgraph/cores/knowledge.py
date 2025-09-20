
from .. schema import KnowledgeResponse, Error, Triples, GraphEmbeddings
from .. knowledge import hash
from .. exceptions import RequestError
from .. tables.knowledge import KnowledgeTableStore
from .. base import Publisher

import base64
import asyncio
import uuid
import logging

# Module logger
logger = logging.getLogger(__name__)

class KnowledgeManager:

    def __init__(
            self, cassandra_host, cassandra_username, cassandra_password,
            keyspace, flow_config,
    ):

        self.table_store = KnowledgeTableStore(
            cassandra_host, cassandra_username, cassandra_password, keyspace
        )

        self.loader_queue = asyncio.Queue(maxsize=20)
        self.background_task = None
        self.flow_config = flow_config

    async def delete_kg_core(self, request, respond):

        logger.info("Deleting knowledge core...")

        await self.table_store.delete_kg_core(
            request.user, request.id
        )

        await respond(
            KnowledgeResponse(
                error = None,
                ids = None,
                eos = False,
                triples = None,
                graph_embeddings = None,
            )
        )

    async def get_kg_core(self, request, respond):

        logger.info("Getting knowledge core...")

        async def publish_triples(t):
            await respond(
                KnowledgeResponse(
                    error = None,
                    ids = None,
                    eos = False,
                    triples = t,
                    graph_embeddings = None,
                )
            )

        # Remove doc table row
        await self.table_store.get_triples(
            request.user,
            request.id,
            publish_triples,
        )

        async def publish_ge(g):
            await respond(
                KnowledgeResponse(
                    error = None,
                    ids = None,
                    eos = False,
                    triples = None,
                    graph_embeddings = g,
                )
            )

        # Remove doc table row
        await self.table_store.get_graph_embeddings(
            request.user,
            request.id,
            publish_ge,
        )

        logger.debug("Knowledge core retrieval complete")

        await respond(
            KnowledgeResponse(
                error = None,
                ids = None,
                eos = True,
                triples = None,
                graph_embeddings = None,
            )
        )

    async def list_kg_cores(self, request, respond):

        ids = await self.table_store.list_kg_cores(request.user)

        await respond(
            KnowledgeResponse(
                error = None,
                ids = ids,
                eos = False,
                triples = None,
                graph_embeddings = None
            )
        )

    async def put_kg_core(self, request, respond):

        if request.triples:
            await self.table_store.add_triples(request.triples)

        if request.graph_embeddings:
            await self.table_store.add_graph_embeddings(
                request.graph_embeddings
            )

        await respond(
            KnowledgeResponse(
                error = None,
                ids = None,
                eos = False,
                triples = None,
                graph_embeddings = None
            )
        )

    async def load_kg_core(self, request, respond):

        if self.background_task is None:
            self.background_task = asyncio.create_task(
                self.core_loader()
            )
            # Wait for it to start (yuck)
#            await asyncio.sleep(0.5)

        await self.loader_queue.put((request, respond))

        # Not sending a response, the loader thread can do that

    async def unload_kg_core(self, request, respond):

        await respond(
            KnowledgeResponse(
                error = Error(
                    type = "not-implemented",
                    message = "Not implemented"
                ),
                ids = None,
                eos = False,
                triples = None,
                graph_embeddings = None
            )
        )

    async def core_loader(self):

        logger.info("Knowledge background processor running...")
        while True:

            logger.debug("Waiting for next load...")
            request, respond = await self.loader_queue.get()

            logger.info(f"Loading knowledge: {request.id}")

            try:

                if request.id is None:
                    raise RuntimeError("Core ID must be specified")

                if request.flow is None:
                    raise RuntimeError("Flow ID must be specified")

                if request.flow not in self.flow_config.flows:
                    raise RuntimeError("Invalid flow")

                flow = self.flow_config.flows[request.flow]

                if "interfaces" not in flow:
                    raise RuntimeError("No defined interfaces")

                if "triples-store" not in flow["interfaces"]:
                    raise RuntimeError("Flow has no triples-store")

                if "graph-embeddings-store" not in flow["interfaces"]:
                    raise RuntimeError("Flow has no graph-embeddings-store")

                t_q = flow["interfaces"]["triples-store"]
                ge_q = flow["interfaces"]["graph-embeddings-store"]

                # Got this far, it should all work
                await respond(
                    KnowledgeResponse(
                        error = None,
                        ids = None,
                        eos = False,
                        triples = None,
                        graph_embeddings = None
                    )
                )

            except Exception as e:

                logger.error(f"Knowledge exception: {e}", exc_info=True)
                await respond(
                    KnowledgeResponse(
                        error = Error(
                            type = "load-error",
                            message = str(e),
                        ),
                        ids = None,
                        eos = False,
                        triples = None,
                        graph_embeddings = None
                    )
                )


            logger.debug("Starting knowledge loading process...")

            try:

                t_pub = None
                ge_pub = None

                logger.debug(f"Triples queue: {t_q}")
                logger.debug(f"Graph embeddings queue: {ge_q}")

                t_pub = Publisher(
                    self.flow_config.pulsar_client, t_q,
                    schema=Triples,
                )
                ge_pub = Publisher(
                    self.flow_config.pulsar_client, ge_q,
                    schema=GraphEmbeddings
                )

                logger.debug("Starting publishers...")

                await t_pub.start()
                await ge_pub.start()

                async def publish_triples(t):
                    # Override collection with request collection
                    if hasattr(t, 'metadata') and hasattr(t.metadata, 'collection'):
                        t.metadata.collection = request.collection or "default"
                    await t_pub.send(None, t)

                logger.debug("Publishing triples...")

                # Remove doc table row
                await self.table_store.get_triples(
                    request.user,
                    request.id,
                    publish_triples,
                )

                async def publish_ge(g):
                    # Override collection with request collection
                    if hasattr(g, 'metadata') and hasattr(g.metadata, 'collection'):
                        g.metadata.collection = request.collection or "default"
                    await ge_pub.send(None, g)

                logger.debug("Publishing graph embeddings...")

                # Remove doc table row
                await self.table_store.get_graph_embeddings(
                    request.user,
                    request.id,
                    publish_ge,
                )

                logger.debug("Knowledge loading completed")

            except Exception as e:

                logger.error(f"Knowledge exception: {e}", exc_info=True)

            finally:

                logger.debug("Stopping publishers...")

                if t_pub: await t_pub.stop()
                if ge_pub: await ge_pub.stop()

            logger.debug("Knowledge processing done")

            continue
