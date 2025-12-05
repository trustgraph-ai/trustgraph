
"""
Graph writer.  Input is graph edge.  Writes edges to FalkorDB graph.
"""

import pulsar
import base64
import os
import argparse
import time
import logging

from falkordb import FalkorDB

from .... base import TriplesStoreService
from .... base import AsyncProcessor, Consumer, Producer
from .... base import ConsumerMetrics, ProducerMetrics
from .... schema import StorageManagementRequest, StorageManagementResponse, Error
from .... schema import triples_storage_management_topic, storage_management_response_topic

# Module logger
logger = logging.getLogger(__name__)

default_ident = "triples-write"

default_graph_url = 'falkor://falkordb:6379'
default_database = 'falkordb'

class Processor(TriplesStoreService):

    def __init__(self, **params):
        
        graph_url = params.get("graph_url", default_graph_url)
        database = params.get("database", default_database)

        super(Processor, self).__init__(
            **params | {
                "graph_url": graph_url,
                "database": database,
            }
        )

        self.db = database

        self.io = FalkorDB.from_url(graph_url).select_graph(database)

        # Set up metrics for storage management
        storage_request_metrics = ConsumerMetrics(
            processor=self.id, flow=None, name="storage-request"
        )
        storage_response_metrics = ProducerMetrics(
            processor=self.id, flow=None, name="storage-response"
        )

        # Set up consumer for storage management requests
        self.storage_request_consumer = Consumer(
            taskgroup=self.taskgroup,
            client=self.pulsar_client,
            flow=None,
            topic=triples_storage_management_topic,
            subscriber=f"{self.id}-storage",
            schema=StorageManagementRequest,
            handler=self.on_storage_management,
            metrics=storage_request_metrics,
        )

        # Set up producer for storage management responses
        self.storage_response_producer = Producer(
            client=self.pulsar_client,
            topic=storage_management_response_topic,
            schema=StorageManagementResponse,
            metrics=storage_response_metrics,
        )

    def create_node(self, uri, user, collection):

        logger.debug(f"Create node {uri} for user={user}, collection={collection}")

        res = self.io.query(
            "MERGE (n:Node {uri: $uri, user: $user, collection: $collection})",
            params={
                "uri": uri,
                "user": user,
                "collection": collection,
            },
        )

        logger.debug("Created {nodes_created} nodes in {time} ms.".format(
            nodes_created=res.nodes_created,
            time=res.run_time_ms
        ))

    def create_literal(self, value, user, collection):

        logger.debug(f"Create literal {value} for user={user}, collection={collection}")

        res = self.io.query(
            "MERGE (n:Literal {value: $value, user: $user, collection: $collection})",
            params={
                "value": value,
                "user": user,
                "collection": collection,
            },
        )

        logger.debug("Created {nodes_created} nodes in {time} ms.".format(
            nodes_created=res.nodes_created,
            time=res.run_time_ms
        ))

    def relate_node(self, src, uri, dest, user, collection):

        logger.debug(f"Create node rel {src} {uri} {dest} for user={user}, collection={collection}")

        res = self.io.query(
            "MATCH (src:Node {uri: $src, user: $user, collection: $collection}) "
            "MATCH (dest:Node {uri: $dest, user: $user, collection: $collection}) "
            "MERGE (src)-[:Rel {uri: $uri, user: $user, collection: $collection}]->(dest)",
            params={
                "src": src,
                "dest": dest,
                "uri": uri,
                "user": user,
                "collection": collection,
            },
        )

        logger.debug("Created {nodes_created} nodes in {time} ms.".format(
            nodes_created=res.nodes_created,
            time=res.run_time_ms
        ))

    def relate_literal(self, src, uri, dest, user, collection):

        logger.debug(f"Create literal rel {src} {uri} {dest} for user={user}, collection={collection}")

        res = self.io.query(
            "MATCH (src:Node {uri: $src, user: $user, collection: $collection}) "
            "MATCH (dest:Literal {value: $dest, user: $user, collection: $collection}) "
            "MERGE (src)-[:Rel {uri: $uri, user: $user, collection: $collection}]->(dest)",
            params={
                "src": src,
                "dest": dest,
                "uri": uri,
                "user": user,
                "collection": collection,
            },
        )

        logger.debug("Created {nodes_created} nodes in {time} ms.".format(
            nodes_created=res.nodes_created,
            time=res.run_time_ms
        ))

    def collection_exists(self, user, collection):
        """Check if collection metadata node exists"""
        result = self.io.query(
            "MATCH (c:CollectionMetadata {user: $user, collection: $collection}) "
            "RETURN c LIMIT 1",
            params={"user": user, "collection": collection}
        )
        return result.result_set is not None and len(result.result_set) > 0

    def create_collection(self, user, collection):
        """Create collection metadata node"""
        import datetime
        self.io.query(
            "MERGE (c:CollectionMetadata {user: $user, collection: $collection}) "
            "SET c.created_at = $created_at",
            params={
                "user": user,
                "collection": collection,
                "created_at": datetime.datetime.now().isoformat()
            }
        )
        logger.info(f"Created collection metadata node for {user}/{collection}")

    async def store_triples(self, message):
        # Extract user and collection from metadata
        user = message.metadata.user if message.metadata.user else "default"
        collection = message.metadata.collection if message.metadata.collection else "default"

        # Validate collection exists before accepting writes
        if not self.collection_exists(user, collection):
            error_msg = (
                f"Collection {collection} does not exist. "
                f"Create it first with tg-set-collection."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        for t in message.triples:

            self.create_node(t.s.value, user, collection)

            if t.o.is_uri:
                self.create_node(t.o.value, user, collection)
                self.relate_node(t.s.value, t.p.value, t.o.value, user, collection)
            else:
                self.create_literal(t.o.value, user, collection)
                self.relate_literal(t.s.value, t.p.value, t.o.value, user, collection)

    @staticmethod
    def add_args(parser):

        TriplesStoreService.add_args(parser)

        parser.add_argument(
            '-g', '--graph-url',
            default=default_graph_url,
            help=f'Graph URL (default: {default_graph_url})'
        )

        parser.add_argument(
            '--database',
            default=default_database,
            help=f'FalkorDB database (default: {default_database})'
        )

    async def start(self):
        """Start the processor and its storage management consumer"""
        await super().start()
        await self.storage_request_consumer.start()
        await self.storage_response_producer.start()

    async def on_storage_management(self, message, consumer, flow):
        """Handle storage management requests"""
        request = message.value()
        logger.info(f"Storage management request: {request.operation} for {request.user}/{request.collection}")

        try:
            if request.operation == "create-collection":
                await self.handle_create_collection(request)
            elif request.operation == "delete-collection":
                await self.handle_delete_collection(request)
            else:
                response = StorageManagementResponse(
                    error=Error(
                        type="invalid_operation",
                        message=f"Unknown operation: {request.operation}"
                    )
                )
                await self.storage_response_producer.send(response)

        except Exception as e:
            logger.error(f"Error processing storage management request: {e}", exc_info=True)
            response = StorageManagementResponse(
                error=Error(
                    type="processing_error",
                    message=str(e)
                )
            )
            await self.storage_response_producer.send(response)

    async def handle_create_collection(self, request):
        """Create collection metadata in FalkorDB"""
        try:
            if self.collection_exists(request.user, request.collection):
                logger.info(f"Collection {request.user}/{request.collection} already exists")
            else:
                self.create_collection(request.user, request.collection)
                logger.info(f"Created collection {request.user}/{request.collection}")

            # Send success response
            response = StorageManagementResponse(error=None)
            await self.storage_response_producer.send(response)

        except Exception as e:
            logger.error(f"Failed to create collection: {e}", exc_info=True)
            response = StorageManagementResponse(
                error=Error(
                    type="creation_error",
                    message=str(e)
                )
            )
            await self.storage_response_producer.send(response)

    async def handle_delete_collection(self, request):
        """Delete the collection for FalkorDB triples"""
        try:
            # Delete all nodes and literals for this user/collection
            node_result = self.io.query(
                "MATCH (n:Node {user: $user, collection: $collection}) DETACH DELETE n",
                params={"user": request.user, "collection": request.collection}
            )

            literal_result = self.io.query(
                "MATCH (n:Literal {user: $user, collection: $collection}) DETACH DELETE n",
                params={"user": request.user, "collection": request.collection}
            )

            # Delete collection metadata node
            metadata_result = self.io.query(
                "MATCH (c:CollectionMetadata {user: $user, collection: $collection}) DELETE c",
                params={"user": request.user, "collection": request.collection}
            )

            logger.info(f"Deleted {node_result.nodes_deleted} nodes, {literal_result.nodes_deleted} literals, and {metadata_result.nodes_deleted} metadata nodes for collection {request.user}/{request.collection}")

            # Send success response
            response = StorageManagementResponse(
                error=None  # No error means success
            )
            await self.storage_response_producer.send(response)
            logger.info(f"Successfully deleted collection {request.user}/{request.collection}")

        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")
            raise

def run():

    Processor.launch(default_ident, __doc__)

