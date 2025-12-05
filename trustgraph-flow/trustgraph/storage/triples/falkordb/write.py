
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

from .... base import TriplesStoreService, CollectionConfigHandler
from .... base import AsyncProcessor, Consumer, Producer
from .... base import ConsumerMetrics, ProducerMetrics

# Module logger
logger = logging.getLogger(__name__)

default_ident = "triples-write"

default_graph_url = 'falkor://falkordb:6379'
default_database = 'falkordb'

class Processor(CollectionConfigHandler, TriplesStoreService):

    def __init__(self, **params):

        graph_url = params.get("graph_url", default_graph_url)
        database = params.get("database", default_database)

        # Initialize collection config handler
        CollectionConfigHandler.__init__(self)

        # Initialize service base class
        TriplesStoreService.__init__(
            self,
            **params | {
                "graph_url": graph_url,
                "database": database,
            }
        )

        self.db = database

        self.io = FalkorDB.from_url(graph_url).select_graph(database)

        # Register for config push notifications
        self.register_config_handler(self.on_collection_config)

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
                f"Create it first via collection management API."
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

    async def create_collection(self, user: str, collection: str, metadata: dict):
        """Create collection metadata in FalkorDB via config push"""
        try:
            # Check if collection exists
            result = self.io.query(
                "MATCH (c:CollectionMetadata {user: $user, collection: $collection}) RETURN c LIMIT 1",
                params={"user": user, "collection": collection}
            )
            if result.result_set:
                logger.info(f"Collection {user}/{collection} already exists")
            else:
                # Create collection metadata node
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
                logger.info(f"Created collection {user}/{collection}")

        except Exception as e:
            logger.error(f"Failed to create collection {user}/{collection}: {e}", exc_info=True)
            raise

    async def delete_collection(self, user: str, collection: str):
        """Delete the collection for FalkorDB triples via config push"""
        try:
            # Delete all nodes and literals for this user/collection
            node_result = self.io.query(
                "MATCH (n:Node {user: $user, collection: $collection}) DETACH DELETE n",
                params={"user": user, "collection": collection}
            )

            literal_result = self.io.query(
                "MATCH (n:Literal {user: $user, collection: $collection}) DETACH DELETE n",
                params={"user": user, "collection": collection}
            )

            # Delete collection metadata node
            metadata_result = self.io.query(
                "MATCH (c:CollectionMetadata {user: $user, collection: $collection}) DELETE c",
                params={"user": user, "collection": collection}
            )

            logger.info(f"Deleted {node_result.nodes_deleted} nodes, {literal_result.nodes_deleted} literals, and {metadata_result.nodes_deleted} metadata nodes for collection {user}/{collection}")

        except Exception as e:
            logger.error(f"Failed to delete collection {user}/{collection}: {e}", exc_info=True)
            raise

def run():

    Processor.launch(default_ident, __doc__)

