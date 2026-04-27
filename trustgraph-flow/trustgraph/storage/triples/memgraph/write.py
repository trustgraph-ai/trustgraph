
"""
Graph writer.  Input is graph edge.  Writes edges to Memgraph.
"""

import base64
import os
import argparse
import time
import logging

from neo4j import GraphDatabase

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


default_graph_host = 'bolt://memgraph:7687'
default_username = 'memgraph'
default_password = 'password'
default_database = 'memgraph'

class Processor(CollectionConfigHandler, TriplesStoreService):

    def __init__(self, **params):

        graph_host = params.get("graph_host", default_graph_host)
        username = params.get("username", default_username)
        password = params.get("password", default_password)
        database = params.get("database", default_database)

        super(Processor, self).__init__(
            **params | {
                "graph_host": graph_host,
                "username": username,
                "password": password,
                "database": database,
            }
        )

        self.db = database

        self.io = GraphDatabase.driver(graph_host, auth=(username, password))

        with self.io.session(database=self.db) as session:
            self.create_indexes(session)

        # Register for config push notifications
        self.register_config_handler(self.on_collection_config, types=["collection"])

    def create_indexes(self, session):

        # Race condition, index creation failure is ignored.  Right thing
        # to do if the index already exists.  Wrong thing to do if it's
        # because the store is not up yet

        # In real-world cases, Memgraph will start up quicker than Pulsar
        # and this process will restart several times until Pulsar arrives,
        # so should be safe

        logger.info("Create indexes...")

        # Legacy indexes for backwards compatibility
        try:
            session.run(
                "CREATE INDEX ON :Node",
            )
        except Exception as e:
            logger.warning(f"Index create failure: {e}")
            # Maybe index already exists
            logger.warning("Index create failure ignored")

        try:
            session.run(
                "CREATE INDEX ON :Node(uri)"
            )
        except Exception as e:
            logger.warning(f"Index create failure: {e}")
            # Maybe index already exists
            logger.warning("Index create failure ignored")

        try:
            session.run(
                "CREATE INDEX ON :Literal",
            )
        except Exception as e:
            logger.warning(f"Index create failure: {e}")
            # Maybe index already exists
            logger.warning("Index create failure ignored")

        try:
            session.run(
                "CREATE INDEX ON :Literal(value)"
            )
        except Exception as e:
            logger.warning(f"Index create failure: {e}")
            # Maybe index already exists
            logger.warning("Index create failure ignored")

        # New indexes for workspace/collection filtering
        try:
            session.run(
                "CREATE INDEX ON :Node(workspace)"
            )
        except Exception as e:
            logger.warning(f"User index create failure: {e}")
            logger.warning("Index create failure ignored")

        try:
            session.run(
                "CREATE INDEX ON :Node(collection)"
            )
        except Exception as e:
            logger.warning(f"Collection index create failure: {e}")
            logger.warning("Index create failure ignored")

        try:
            session.run(
                "CREATE INDEX ON :Literal(workspace)"
            )
        except Exception as e:
            logger.warning(f"User index create failure: {e}")
            logger.warning("Index create failure ignored")

        try:
            session.run(
                "CREATE INDEX ON :Literal(collection)"
            )
        except Exception as e:
            logger.warning(f"Collection index create failure: {e}")
            logger.warning("Index create failure ignored")

        logger.info("Index creation done")

    def create_node(self, uri, workspace, collection):

        logger.debug(f"Create node {uri} for workspace={workspace}, collection={collection}")

        summary = self.io.execute_query(
            "MERGE (n:Node {uri: $uri, workspace: $workspace, collection: $collection})",
            uri=uri, workspace=workspace, collection=collection,
            database_=self.db,
        ).summary

        logger.debug("Created {nodes_created} nodes in {time} ms.".format(
            nodes_created=summary.counters.nodes_created,
            time=summary.result_available_after
        ))

    def create_literal(self, value, workspace, collection):

        logger.debug(f"Create literal {value} for workspace={workspace}, collection={collection}")

        summary = self.io.execute_query(
            "MERGE (n:Literal {value: $value, workspace: $workspace, collection: $collection})",
            value=value, workspace=workspace, collection=collection,
            database_=self.db,
        ).summary

        logger.debug("Created {nodes_created} nodes in {time} ms.".format(
            nodes_created=summary.counters.nodes_created,
            time=summary.result_available_after
        ))

    def relate_node(self, src, uri, dest, workspace, collection):

        logger.debug(f"Create node rel {src} {uri} {dest} for workspace={workspace}, collection={collection}")

        summary = self.io.execute_query(
            "MATCH (src:Node {uri: $src, workspace: $workspace, collection: $collection}) "
            "MATCH (dest:Node {uri: $dest, workspace: $workspace, collection: $collection}) "
            "MERGE (src)-[:Rel {uri: $uri, workspace: $workspace, collection: $collection}]->(dest)",
            src=src, dest=dest, uri=uri, workspace=workspace, collection=collection,
            database_=self.db,
        ).summary

        logger.debug("Created {nodes_created} nodes in {time} ms.".format(
            nodes_created=summary.counters.nodes_created,
            time=summary.result_available_after
        ))

    def relate_literal(self, src, uri, dest, workspace, collection):

        logger.debug(f"Create literal rel {src} {uri} {dest} for workspace={workspace}, collection={collection}")

        summary = self.io.execute_query(
            "MATCH (src:Node {uri: $src, workspace: $workspace, collection: $collection}) "
            "MATCH (dest:Literal {value: $dest, workspace: $workspace, collection: $collection}) "
            "MERGE (src)-[:Rel {uri: $uri, workspace: $workspace, collection: $collection}]->(dest)",
            src=src, dest=dest, uri=uri, workspace=workspace, collection=collection,
            database_=self.db,
        ).summary

        logger.debug("Created {nodes_created} nodes in {time} ms.".format(
            nodes_created=summary.counters.nodes_created,
            time=summary.result_available_after
        ))

    def create_triple(self, tx, t, workspace, collection):

        s_val = get_term_value(t.s)
        p_val = get_term_value(t.p)
        o_val = get_term_value(t.o)

        # Create new s node with given uri, if not exists
        result = tx.run(
            "MERGE (n:Node {uri: $uri, workspace: $workspace, collection: $collection})",
            uri=s_val, workspace=workspace, collection=collection
        )

        if t.o.type == IRI:

            # Create new o node with given uri, if not exists
            result = tx.run(
                "MERGE (n:Node {uri: $uri, workspace: $workspace, collection: $collection})",
                uri=o_val, workspace=workspace, collection=collection
            )

            result = tx.run(
                "MATCH (src:Node {uri: $src, workspace: $workspace, collection: $collection}) "
                "MATCH (dest:Node {uri: $dest, workspace: $workspace, collection: $collection}) "
                "MERGE (src)-[:Rel {uri: $uri, workspace: $workspace, collection: $collection}]->(dest)",
                src=s_val, dest=o_val, uri=p_val, workspace=workspace, collection=collection,
            )

        else:

            # Create new o literal with given uri, if not exists
            result = tx.run(
                "MERGE (n:Literal {value: $value, workspace: $workspace, collection: $collection})",
                value=o_val, workspace=workspace, collection=collection
            )

            result = tx.run(
                "MATCH (src:Node {uri: $src, workspace: $workspace, collection: $collection}) "
                "MATCH (dest:Literal {value: $dest, workspace: $workspace, collection: $collection}) "
                "MERGE (src)-[:Rel {uri: $uri, workspace: $workspace, collection: $collection}]->(dest)",
                src=s_val, dest=o_val, uri=p_val, workspace=workspace, collection=collection,
            )
        
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

            # Alternative implementation using transactions
            # with self.io.session(database=self.db) as session:
            #     session.execute_write(self.create_triple, t, workspace, collection)

    @staticmethod
    def add_args(parser):

        TriplesStoreService.add_args(parser)

        parser.add_argument(
            '-g', '--graph-host',
            default=default_graph_host,
            help=f'Graph host (default: {default_graph_host})'
        )

        parser.add_argument(
            '--username',
            default=default_username,
            help=f'Memgraph username (default: {default_username})'
        )

        parser.add_argument(
            '--password',
            default=default_password,
            help=f'Memgraph password (default: {default_password})'
        )

        parser.add_argument(
            '--database',
            default=default_database,
            help=f'Memgraph database (default: {default_database})'
        )

    def _collection_exists_in_db(self, workspace, collection):
        """Check if collection metadata node exists"""
        with self.io.session(database=self.db) as session:
            result = session.run(
                "MATCH (c:CollectionMetadata {workspace: $workspace, collection: $collection}) "
                "RETURN c LIMIT 1",
                workspace=workspace, collection=collection
            )
            return bool(list(result))

    def _create_collection_in_db(self, workspace, collection):
        """Create collection metadata node"""
        import datetime
        with self.io.session(database=self.db) as session:
            session.run(
                "MERGE (c:CollectionMetadata {workspace: $workspace, collection: $collection}) "
                "SET c.created_at = $created_at",
                workspace=workspace, collection=collection,
                created_at=datetime.datetime.now().isoformat()
            )
            logger.info(f"Created collection metadata node for {workspace}/{collection}")

    async def create_collection(self, workspace: str, collection: str, metadata: dict):
        """Create collection metadata in Memgraph via config push"""
        try:
            if self._collection_exists_in_db(workspace, collection):
                logger.info(f"Collection {workspace}/{collection} already exists")
            else:
                self._create_collection_in_db(workspace, collection)
                logger.info(f"Created collection {workspace}/{collection}")

        except Exception as e:
            logger.error(f"Failed to create collection {workspace}/{collection}: {e}", exc_info=True)
            raise

    async def delete_collection(self, workspace: str, collection: str):
        """Delete all data for a specific collection via config push"""
        try:
            with self.io.session(database=self.db) as session:
                # Delete all nodes for this workspace and collection
                node_result = session.run(
                    "MATCH (n:Node {workspace: $workspace, collection: $collection}) "
                    "DETACH DELETE n",
                    workspace=workspace, collection=collection
                )
                nodes_deleted = node_result.consume().counters.nodes_deleted

                # Delete all literals for this workspace and collection
                literal_result = session.run(
                    "MATCH (n:Literal {workspace: $workspace, collection: $collection}) "
                    "DETACH DELETE n",
                    workspace=workspace, collection=collection
                )
                literals_deleted = literal_result.consume().counters.nodes_deleted

                # Delete collection metadata node
                metadata_result = session.run(
                    "MATCH (c:CollectionMetadata {workspace: $workspace, collection: $collection}) "
                    "DELETE c",
                    workspace=workspace, collection=collection
                )
                metadata_deleted = metadata_result.consume().counters.nodes_deleted

                # Note: Relationships are automatically deleted with DETACH DELETE

                logger.info(f"Deleted {nodes_deleted} nodes, {literals_deleted} literals, and {metadata_deleted} metadata nodes for {workspace}/{collection}")

        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")
            raise

def run():

    Processor.launch(default_ident, __doc__)

