
from .. schema import KnowledgeResponse, Error, Triples, GraphEmbeddings
from .. schema import DocumentEmbeddings
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
            keyspace, flow_config, replication_factor=1,
    ):

        self.table_store = KnowledgeTableStore(
            cassandra_host, cassandra_username, cassandra_password, keyspace,
            replication_factor
        )

        self.loader_queue = asyncio.Queue(maxsize=20)
        self.background_task = None
        self.flow_config = flow_config

    async def delete_kg_core(self, request, respond, workspace):

        logger.info("Deleting knowledge core...")

        await self.table_store.delete_kg_core(
            workspace, request.id
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

    async def get_kg_core(self, request, respond, workspace):

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

        await self.table_store.get_triples(
            workspace,
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

        await self.table_store.get_graph_embeddings(
            workspace,
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

    async def list_kg_cores(self, request, respond, workspace):

        ids = await self.table_store.list_kg_cores(workspace)

        await respond(
            KnowledgeResponse(
                error = None,
                ids = ids,
                eos = False,
                triples = None,
                graph_embeddings = None
            )
        )

    async def put_kg_core(self, request, respond, workspace):

        if request.triples:
            await self.table_store.add_triples(workspace, request.triples)

        if request.graph_embeddings:
            await self.table_store.add_graph_embeddings(
                workspace, request.graph_embeddings
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

    async def load_kg_core(self, request, respond, workspace):

        if self.background_task is None:
            self.background_task = asyncio.create_task(
                self.core_loader()
            )

        await self.loader_queue.put((request, respond, workspace))

        # Not sending a response, the loader thread can do that

    async def unload_kg_core(self, request, respond, workspace):

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

    async def list_de_cores(self, request, respond, workspace):

        ids = await self.table_store.list_de_cores(workspace)

        await respond(
            KnowledgeResponse(
                error = None,
                ids = ids,
                eos = False,
                triples = None,
                graph_embeddings = None,
            )
        )

    async def get_de_core(self, request, respond, workspace):

        logger.info("Getting document embeddings core...")

        async def publish_de(de):
            await respond(
                KnowledgeResponse(
                    error = None,
                    ids = None,
                    eos = False,
                    triples = None,
                    graph_embeddings = None,
                    document_embeddings = de,
                )
            )

        await self.table_store.get_document_embeddings(
            workspace,
            request.id,
            publish_de,
        )

        logger.debug("Document embeddings core retrieval complete")

        await respond(
            KnowledgeResponse(
                error = None,
                ids = None,
                eos = True,
                triples = None,
                graph_embeddings = None,
            )
        )

    async def put_de_core(self, request, respond, workspace):

        if request.document_embeddings:
            await self.table_store.add_document_embeddings(
                workspace, request.document_embeddings
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

    async def delete_de_core(self, request, respond, workspace):

        logger.info("Deleting document embeddings core...")

        await self.table_store.delete_document_embeddings(
            workspace, request.id
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

    async def load_de_core(self, request, respond, workspace):

        if self.background_task is None:
            self.background_task = asyncio.create_task(
                self.core_loader()
            )

        await self.loader_queue.put((request, respond, workspace))

    async def core_loader(self):

        logger.info("Knowledge background processor running...")
        while True:

            logger.debug("Waiting for next load...")
            request, respond, workspace = await self.loader_queue.get()

            logger.info(f"Loading: {request.operation} {request.id}")

            try:

                if request.id is None:
                    raise RuntimeError("Core ID must be specified")

                if request.flow is None:
                    raise RuntimeError("Flow ID must be specified")

                ws_flows = self.flow_config.flows.get(workspace, {})
                if request.flow not in ws_flows:
                    raise RuntimeError(
                        f"Invalid flow {request.flow} for workspace "
                        f"{workspace}"
                    )

                flow = ws_flows[request.flow]

                if "interfaces" not in flow:
                    raise RuntimeError("No defined interfaces")

                if request.operation == "load-de-core":
                    await self._load_de_core(
                        request, respond, workspace, flow,
                    )
                else:
                    await self._load_kg_core(
                        request, respond, workspace, flow,
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

            logger.debug("Knowledge processing done")

            continue

    async def _load_kg_core(self, request, respond, workspace, flow):

        if "triples-store" not in flow["interfaces"]:
            raise RuntimeError("Flow has no triples-store")

        if "graph-embeddings-store" not in flow["interfaces"]:
            raise RuntimeError("Flow has no graph-embeddings-store")

        t_q = flow["interfaces"]["triples-store"]["flow"]
        ge_q = flow["interfaces"]["graph-embeddings-store"]["flow"]

        await respond(
            KnowledgeResponse(
                error = None,
                ids = None,
                eos = False,
                triples = None,
                graph_embeddings = None
            )
        )

        t_pub = None
        ge_pub = None

        try:

            logger.debug(f"Triples queue: {t_q}")
            logger.debug(f"Graph embeddings queue: {ge_q}")

            t_pub = Publisher(
                self.flow_config.pubsub, t_q,
                schema=Triples,
            )
            ge_pub = Publisher(
                self.flow_config.pubsub, ge_q,
                schema=GraphEmbeddings
            )

            logger.debug("Starting publishers...")

            await t_pub.start()
            await ge_pub.start()

            async def publish_triples(t):
                if hasattr(t, 'metadata') and hasattr(t.metadata, 'collection'):
                    t.metadata.collection = request.collection or "default"
                await t_pub.send(None, t)

            logger.debug("Publishing triples...")

            await self.table_store.get_triples(
                workspace,
                request.id,
                publish_triples,
            )

            async def publish_ge(g):
                if hasattr(g, 'metadata') and hasattr(g.metadata, 'collection'):
                    g.metadata.collection = request.collection or "default"
                await ge_pub.send(None, g)

            logger.debug("Publishing graph embeddings...")

            await self.table_store.get_graph_embeddings(
                workspace,
                request.id,
                publish_ge,
            )

            logger.debug("Knowledge core loading completed")

        except Exception as e:

            logger.error(f"Knowledge exception: {e}", exc_info=True)

        finally:

            logger.debug("Stopping publishers...")

            if t_pub: await t_pub.stop()
            if ge_pub: await ge_pub.stop()

    async def _load_de_core(self, request, respond, workspace, flow):

        if "document-embeddings-store" not in flow["interfaces"]:
            raise RuntimeError("Flow has no document-embeddings-store")

        de_q = flow["interfaces"]["document-embeddings-store"]["flow"]

        await respond(
            KnowledgeResponse(
                error = None,
                ids = None,
                eos = False,
                triples = None,
                graph_embeddings = None
            )
        )

        de_pub = None

        try:

            logger.debug(f"Document embeddings queue: {de_q}")

            de_pub = Publisher(
                self.flow_config.pubsub, de_q,
                schema=DocumentEmbeddings,
            )

            logger.debug("Starting publisher...")

            await de_pub.start()

            async def publish_de(de):
                if hasattr(de, 'metadata') and hasattr(de.metadata, 'collection'):
                    de.metadata.collection = request.collection or "default"
                await de_pub.send(None, de)

            logger.debug("Publishing document embeddings...")

            await self.table_store.get_document_embeddings(
                workspace,
                request.id,
                publish_de,
            )

            logger.debug("Document embeddings core loading completed")

        except Exception as e:

            logger.error(f"Knowledge exception: {e}", exc_info=True)

        finally:

            logger.debug("Stopping publisher...")

            if de_pub: await de_pub.stop()
