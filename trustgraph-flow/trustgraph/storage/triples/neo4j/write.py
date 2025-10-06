
"""
Graph writer.  Input is graph edge.  Writes edges to Neo4j graph.
"""

import pulsar
import base64
import os
import argparse
import time
import logging

from neo4j import GraphDatabase
from .... base import TriplesStoreService
from .... base import AsyncProcessor, Consumer, Producer
from .... base import ConsumerMetrics, ProducerMetrics
from .... schema import StorageManagementRequest, StorageManagementResponse, Error
from .... schema import triples_storage_management_topic, storage_management_response_topic

# Module logger
logger = logging.getLogger(__name__)

default_ident = "triples-write"

default_graph_host = 'bolt://neo4j:7687'
default_username = 'neo4j'
default_password = 'password'
default_database = 'neo4j'

class Processor(TriplesStoreService):

    def __init__(self, **params):
        
        id = params.get("id", default_ident)

        graph_host = params.get("graph_host", default_graph_host)
        username = params.get("username", default_username)
        password = params.get("password", default_password)
        database = params.get("database", default_database)

        super(Processor, self).__init__(
            **params | {
                "graph_host": graph_host,
                "username": username,
                "database": database,
            }
        )

        self.db = database

        self.io = GraphDatabase.driver(graph_host, auth=(username, password))

        with self.io.session(database=self.db) as session:
            self.create_indexes(session)

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
            subscriber=f"{id}-storage",
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

    def create_indexes(self, session):

        # Race condition, index creation failure is ignored.  Right thing
        # to do if the index already exists.  Wrong thing to do if it's
        # because the store is not up yet

        # In real-world cases, Neo4j will start up quicker than Pulsar
        # and this process will restart several times until Pulsar arrives,
        # so should be safe

        logger.info("Create indexes...")

        # Legacy indexes for backwards compatibility
        try:
            session.run(
                "CREATE INDEX Node_uri FOR (n:Node) ON (n.uri)",
            )
        except Exception as e:
            logger.warning(f"Index create failure: {e}")
            # Maybe index already exists
            logger.warning("Index create failure ignored")

        try:
            session.run(
                "CREATE INDEX Literal_value FOR (n:Literal) ON (n.value)",
            )
        except Exception as e:
            logger.warning(f"Index create failure: {e}")
            # Maybe index already exists
            logger.warning("Index create failure ignored")

        try:
            session.run(
                "CREATE INDEX Rel_uri FOR ()-[r:Rel]-() ON (r.uri)",
            )
        except Exception as e:
            logger.warning(f"Index create failure: {e}")
            # Maybe index already exists
            logger.warning("Index create failure ignored")

        # New compound indexes for user/collection filtering
        try:
            session.run(
                "CREATE INDEX node_user_collection_uri FOR (n:Node) ON (n.user, n.collection, n.uri)",
            )
        except Exception as e:
            logger.warning(f"Compound index create failure: {e}")
            logger.warning("Index create failure ignored")

        try:
            session.run(
                "CREATE INDEX literal_user_collection_value FOR (n:Literal) ON (n.user, n.collection, n.value)",
            )
        except Exception as e:
            logger.warning(f"Compound index create failure: {e}")
            logger.warning("Index create failure ignored")

        # Note: Neo4j doesn't support compound indexes on relationships in all versions
        # Try to create individual indexes on relationship properties
        try:
            session.run(
                "CREATE INDEX rel_user FOR ()-[r:Rel]-() ON (r.user)",
            )
        except Exception as e:
            logger.warning(f"Relationship index create failure: {e}")
            logger.warning("Index create failure ignored")

        try:
            session.run(
                "CREATE INDEX rel_collection FOR ()-[r:Rel]-() ON (r.collection)",
            )
        except Exception as e:
            logger.warning(f"Relationship index create failure: {e}")
            logger.warning("Index create failure ignored")

        logger.info("Index creation done")

    def create_node(self, uri, user, collection):

        logger.debug(f"Create node {uri} for user={user}, collection={collection}")

        summary = self.io.execute_query(
            "MERGE (n:Node {uri: $uri, user: $user, collection: $collection})",
            uri=uri, user=user, collection=collection,
            database_=self.db,
        ).summary

        logger.debug("Created {nodes_created} nodes in {time} ms.".format(
            nodes_created=summary.counters.nodes_created,
            time=summary.result_available_after
        ))

    def create_literal(self, value, user, collection):

        logger.debug(f"Create literal {value} for user={user}, collection={collection}")

        summary = self.io.execute_query(
            "MERGE (n:Literal {value: $value, user: $user, collection: $collection})",
            value=value, user=user, collection=collection,
            database_=self.db,
        ).summary

        logger.debug("Created {nodes_created} nodes in {time} ms.".format(
            nodes_created=summary.counters.nodes_created,
            time=summary.result_available_after
        ))

    def relate_node(self, src, uri, dest, user, collection):

        logger.debug(f"Create node rel {src} {uri} {dest} for user={user}, collection={collection}")

        summary = self.io.execute_query(
            "MATCH (src:Node {uri: $src, user: $user, collection: $collection}) "
            "MATCH (dest:Node {uri: $dest, user: $user, collection: $collection}) "
            "MERGE (src)-[:Rel {uri: $uri, user: $user, collection: $collection}]->(dest)",
            src=src, dest=dest, uri=uri, user=user, collection=collection,
            database_=self.db,
        ).summary

        logger.debug("Created {nodes_created} nodes in {time} ms.".format(
            nodes_created=summary.counters.nodes_created,
            time=summary.result_available_after
        ))

    def relate_literal(self, src, uri, dest, user, collection):

        logger.debug(f"Create literal rel {src} {uri} {dest} for user={user}, collection={collection}")

        summary = self.io.execute_query(
            "MATCH (src:Node {uri: $src, user: $user, collection: $collection}) "
            "MATCH (dest:Literal {value: $dest, user: $user, collection: $collection}) "
            "MERGE (src)-[:Rel {uri: $uri, user: $user, collection: $collection}]->(dest)",
            src=src, dest=dest, uri=uri, user=user, collection=collection,
            database_=self.db,
        ).summary

        logger.debug("Created {nodes_created} nodes in {time} ms.".format(
            nodes_created=summary.counters.nodes_created,
            time=summary.result_available_after
        ))

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
            '-g', '--graph_host',
            default=default_graph_host,
            help=f'Graph host (default: {default_graph_host})'
        )

        parser.add_argument(
            '--username',
            default=default_username,
            help=f'Neo4j username (default: {default_username})'
        )

        parser.add_argument(
            '--password',
            default=default_password,
            help=f'Neo4j password (default: {default_password})'
        )

        parser.add_argument(
            '--database',
            default=default_database,
            help=f'Neo4j database (default: {default_database})'
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

    def collection_exists(self, user, collection):
        """Check if collection metadata node exists"""
        with self.io.session(database=self.db) as session:
            result = session.run(
                "MATCH (c:CollectionMetadata {user: $user, collection: $collection}) "
                "RETURN c LIMIT 1",
                user=user, collection=collection
            )
            return bool(list(result))

    def create_collection(self, user, collection):
        """Create collection metadata node"""
        import datetime
        with self.io.session(database=self.db) as session:
            session.run(
                "MERGE (c:CollectionMetadata {user: $user, collection: $collection}) "
                "SET c.created_at = $created_at",
                user=user, collection=collection,
                created_at=datetime.datetime.now().isoformat()
            )
            logger.info(f"Created collection metadata node for {user}/{collection}")

    async def handle_create_collection(self, request):
        """Create collection metadata in Neo4j"""
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
        """Delete all data for a specific collection"""
        try:
            with self.io.session(database=self.db) as session:
                # Delete all nodes for this user and collection
                node_result = session.run(
                    "MATCH (n:Node {user: $user, collection: $collection}) "
                    "DETACH DELETE n",
                    user=request.user, collection=request.collection
                )
                nodes_deleted = node_result.consume().counters.nodes_deleted

                # Delete all literals for this user and collection
                literal_result = session.run(
                    "MATCH (n:Literal {user: $user, collection: $collection}) "
                    "DETACH DELETE n",
                    user=request.user, collection=request.collection
                )
                literals_deleted = literal_result.consume().counters.nodes_deleted

                # Note: Relationships are automatically deleted with DETACH DELETE

                # Delete collection metadata node
                metadata_result = session.run(
                    "MATCH (c:CollectionMetadata {user: $user, collection: $collection}) "
                    "DELETE c",
                    user=request.user, collection=request.collection
                )
                metadata_deleted = metadata_result.consume().counters.nodes_deleted

                logger.info(f"Deleted {nodes_deleted} nodes, {literals_deleted} literals, and {metadata_deleted} metadata nodes for {request.user}/{request.collection}")

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

