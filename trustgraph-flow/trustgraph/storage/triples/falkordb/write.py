
"""
Graph writer.  Input is graph edge.  Writes edges to FalkorDB graph.
"""

import base64
import os
import argparse
import time
import logging

from falkordb import FalkorDB

from .... base import TriplesStoreService, CollectionConfigHandler
from .... base import AsyncProcessor, Consumer, Producer
from .... base import ConsumerMetrics, ProducerMetrics
from .... schema import IRI, LITERAL

# Module logger
logger = logging.getLogger(__name__)

default_ident = "triples-write"


def get_term_value(term):
    """Extract the string value from a Term"""
    if term is None:
        return None
    if term.type == IRI:
        return term.iri
    elif term.type == LITERAL:
        return term.value
    else:
        # For blank nodes or other types, use id or value
        return term.id or term.value


default_graph_url = 'falkor://falkordb:6379'
default_database = 'falkordb'

class Processor(CollectionConfigHandler, TriplesStoreService):

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

        # Register for config push notifications
        self.register_config_handler(self.on_collection_config, types=["collection"])

    def create_node(self, uri, workspace, collection):

        logger.debug(f"Create node {uri} for workspace={workspace}, collection={collection}")

        res = self.io.query(
            "MERGE (n:Node {uri: $uri, workspace: $workspace, collection: $collection})",
            params={
                "uri": uri,
                "workspace": workspace,
                "collection": collection,
            },
        )

        logger.debug("Created {nodes_created} nodes in {time} ms.".format(
            nodes_created=res.nodes_created,
            time=res.run_time_ms
        ))

    def create_literal(self, value, workspace, collection):

        logger.debug(f"Create literal {value} for workspace={workspace}, collection={collection}")

        res = self.io.query(
            "MERGE (n:Literal {value: $value, workspace: $workspace, collection: $collection})",
            params={
                "value": value,
                "workspace": workspace,
                "collection": collection,
            },
        )

        logger.debug("Created {nodes_created} nodes in {time} ms.".format(
            nodes_created=res.nodes_created,
            time=res.run_time_ms
        ))

    def relate_node(self, src, uri, dest, workspace, collection):

        logger.debug(f"Create node rel {src} {uri} {dest} for workspace={workspace}, collection={collection}")

        res = self.io.query(
            "MATCH (src:Node {uri: $src, workspace: $workspace, collection: $collection}) "
            "MATCH (dest:Node {uri: $dest, workspace: $workspace, collection: $collection}) "
            "MERGE (src)-[:Rel {uri: $uri, workspace: $workspace, collection: $collection}]->(dest)",
            params={
                "src": src,
                "dest": dest,
                "uri": uri,
                "workspace": workspace,
                "collection": collection,
            },
        )

        logger.debug("Created {nodes_created} nodes in {time} ms.".format(
            nodes_created=res.nodes_created,
            time=res.run_time_ms
        ))

    def relate_literal(self, src, uri, dest, workspace, collection):

        logger.debug(f"Create literal rel {src} {uri} {dest} for workspace={workspace}, collection={collection}")

        res = self.io.query(
            "MATCH (src:Node {uri: $src, workspace: $workspace, collection: $collection}) "
            "MATCH (dest:Literal {value: $dest, workspace: $workspace, collection: $collection}) "
            "MERGE (src)-[:Rel {uri: $uri, workspace: $workspace, collection: $collection}]->(dest)",
            params={
                "src": src,
                "dest": dest,
                "uri": uri,
                "workspace": workspace,
                "collection": collection,
            },
        )

        logger.debug("Created {nodes_created} nodes in {time} ms.".format(
            nodes_created=res.nodes_created,
            time=res.run_time_ms
        ))

    def collection_exists(self, workspace, collection):
        """Check if collection metadata node exists"""
        result = self.io.query(
            "MATCH (c:CollectionMetadata {workspace: $workspace, collection: $collection}) "
            "RETURN c LIMIT 1",
            params={"workspace": workspace, "collection": collection}
        )
        return result.result_set is not None and len(result.result_set) > 0

    def create_collection(self, workspace, collection):
        """Create collection metadata node"""
        import datetime
        self.io.query(
            "MERGE (c:CollectionMetadata {workspace: $workspace, collection: $collection}) "
            "SET c.created_at = $created_at",
            params={
                "workspace": workspace,
                "collection": collection,
                "created_at": datetime.datetime.now().isoformat()
            }
        )
        logger.info(f"Created collection metadata node for {workspace}/{collection}")

    async def store_triples(self, workspace, message):
        collection = message.metadata.collection if message.metadata.collection else "default"

        # Validate collection exists before accepting writes
        if not self.collection_exists(workspace, collection):
            error_msg = (
                f"Collection {collection} does not exist. "
                f"Create it first via collection management API."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        for t in message.triples:

            s_val = get_term_value(t.s)
            p_val = get_term_value(t.p)
            o_val = get_term_value(t.o)

            self.create_node(s_val, workspace, collection)

            if t.o.type == IRI:
                self.create_node(o_val, workspace, collection)
                self.relate_node(s_val, p_val, o_val, workspace, collection)
            else:
                self.create_literal(o_val, workspace, collection)
                self.relate_literal(s_val, p_val, o_val, workspace, collection)

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

    async def create_collection(self, workspace: str, collection: str, metadata: dict):
        """Create collection metadata in FalkorDB via config push"""
        try:
            # Check if collection exists
            result = self.io.query(
                "MATCH (c:CollectionMetadata {workspace: $workspace, collection: $collection}) RETURN c LIMIT 1",
                params={"workspace": workspace, "collection": collection}
            )
            if result.result_set:
                logger.info(f"Collection {workspace}/{collection} already exists")
            else:
                # Create collection metadata node
                import datetime
                self.io.query(
                    "MERGE (c:CollectionMetadata {workspace: $workspace, collection: $collection}) "
                    "SET c.created_at = $created_at",
                    params={
                        "workspace": workspace,
                        "collection": collection,
                        "created_at": datetime.datetime.now().isoformat()
                    }
                )
                logger.info(f"Created collection {workspace}/{collection}")

        except Exception as e:
            logger.error(f"Failed to create collection {workspace}/{collection}: {e}", exc_info=True)
            raise

    async def delete_collection(self, workspace: str, collection: str):
        """Delete the collection for FalkorDB triples via config push"""
        try:
            # Delete all nodes and literals for this workspace/collection
            node_result = self.io.query(
                "MATCH (n:Node {workspace: $workspace, collection: $collection}) DETACH DELETE n",
                params={"workspace": workspace, "collection": collection}
            )

            literal_result = self.io.query(
                "MATCH (n:Literal {workspace: $workspace, collection: $collection}) DETACH DELETE n",
                params={"workspace": workspace, "collection": collection}
            )

            # Delete collection metadata node
            metadata_result = self.io.query(
                "MATCH (c:CollectionMetadata {workspace: $workspace, collection: $collection}) DELETE c",
                params={"workspace": workspace, "collection": collection}
            )

            logger.info(f"Deleted {node_result.nodes_deleted} nodes, {literal_result.nodes_deleted} literals, and {metadata_result.nodes_deleted} metadata nodes for collection {workspace}/{collection}")

        except Exception as e:
            logger.error(f"Failed to delete collection {workspace}/{collection}: {e}", exc_info=True)
            raise

def run():

    Processor.launch(default_ident, __doc__)

