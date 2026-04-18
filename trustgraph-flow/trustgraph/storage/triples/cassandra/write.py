
"""
Graph writer.  Input is graph edge.  Writes edges to Cassandra graph.
"""

import asyncio
import base64
import os
import argparse
import time
import logging
import json

from .... direct.cassandra_kg import (
    EntityCentricKnowledgeGraph, DEFAULT_GRAPH
)
from .... base import TriplesStoreService, CollectionConfigHandler
from .... base import AsyncProcessor, Consumer, Producer
from .... base import ConsumerMetrics, ProducerMetrics
from .... base.cassandra_config import add_cassandra_args, resolve_cassandra_config
from .... schema import IRI, LITERAL, BLANK, TRIPLE

# Module logger
logger = logging.getLogger(__name__)

default_ident = "triples-write"


def serialize_triple(triple):
    """Serialize a Triple object to JSON for storage."""
    if triple is None:
        return None

    def term_to_dict(term):
        if term is None:
            return None

        result = {"type": term.type}
        if term.type == IRI:
            result["iri"] = term.iri
        elif term.type == LITERAL:
            result["value"] = term.value
            if term.datatype:
                result["datatype"] = term.datatype
            if term.language:
                result["language"] = term.language
        elif term.type == BLANK:
            result["id"] = term.id
        elif term.type == TRIPLE:
            result["triple"] = serialize_triple(term.triple)
        return result

    return json.dumps({
        "s": term_to_dict(triple.s),
        "p": term_to_dict(triple.p),
        "o": term_to_dict(triple.o),
    })


def get_term_value(term):
    """Extract the string value from a Term"""
    if term is None:
        return None
    if term.type == IRI:
        return term.iri
    elif term.type == LITERAL:
        return term.value
    elif term.type == TRIPLE:
        # Serialize nested triple as JSON
        return serialize_triple(term.triple)
    else:
        # For blank nodes or other types, use id or value
        return term.id or term.value


def get_term_otype(term):
    """
    Get object type code from a Term for entity-centric storage.

    Maps Term.type to otype:
    - IRI ("i") → "u" (URI)
    - BLANK ("b") → "u" (treated as URI)
    - LITERAL ("l") → "l" (Literal)
    - TRIPLE ("t") → "t" (Triple/reification)
    """
    if term is None:
        return "u"
    if term.type == IRI or term.type == BLANK:
        return "u"
    elif term.type == LITERAL:
        return "l"
    elif term.type == TRIPLE:
        return "t"
    else:
        return "u"


def get_term_dtype(term):
    """Extract datatype from a Term (for literals)"""
    if term is None:
        return ""
    if term.type == LITERAL:
        return term.datatype or ""
    return ""


def get_term_lang(term):
    """Extract language tag from a Term (for literals)"""
    if term is None:
        return ""
    if term.type == LITERAL:
        return term.language or ""
    return ""


class Processor(CollectionConfigHandler, TriplesStoreService):

    def __init__(self, **params):

        id = params.get("id", default_ident)

        # Get Cassandra parameters
        cassandra_host = params.get("cassandra_host")
        cassandra_username = params.get("cassandra_username")
        cassandra_password = params.get("cassandra_password")

        # Resolve configuration with environment variable fallback
        hosts, username, password, keyspace = resolve_cassandra_config(
            host=cassandra_host,
            username=cassandra_username,
            password=cassandra_password
        )

        super(Processor, self).__init__(
            **params | {
                "cassandra_host": ','.join(hosts),
                "cassandra_username": username
            }
        )

        self.cassandra_host = hosts
        self.cassandra_username = username
        self.cassandra_password = password
        self.table = None
        self.tg = None

        # Register for config push notifications
        self.register_config_handler(self.on_collection_config, types=["collection"])

    async def store_triples(self, workspace, message):

        # The cassandra-driver work below — connection, schema
        # setup, and per-triple inserts — is all synchronous.
        # Wrap the whole batch in a worker thread so the event
        # loop stays responsive for sibling processors when
        # running in a processor group.

        def _do_store():

            if self.table is None or self.table != workspace:

                self.tg = None

                # Use factory function to select implementation
                KGClass = EntityCentricKnowledgeGraph

                try:
                    if self.cassandra_username and self.cassandra_password:
                        self.tg = KGClass(
                            hosts=self.cassandra_host,
                            keyspace=workspace,
                            username=self.cassandra_username,
                            password=self.cassandra_password,
                        )
                    else:
                        self.tg = KGClass(
                            hosts=self.cassandra_host,
                            keyspace=workspace,
                        )
                except Exception as e:
                    logger.error(f"Exception: {e}", exc_info=True)
                    time.sleep(1)
                    raise e

                self.table = workspace

            for t in message.triples:
                # Extract values from Term objects
                s_val = get_term_value(t.s)
                p_val = get_term_value(t.p)
                o_val = get_term_value(t.o)
                # t.g is None for default graph, or a graph IRI
                g_val = t.g if t.g is not None else DEFAULT_GRAPH

                # Extract object type metadata for entity-centric storage
                otype = get_term_otype(t.o)
                dtype = get_term_dtype(t.o)
                lang = get_term_lang(t.o)

                self.tg.insert(
                    message.metadata.collection,
                    s_val,
                    p_val,
                    o_val,
                    g=g_val,
                    otype=otype,
                    dtype=dtype,
                    lang=lang,
                )

        await asyncio.to_thread(_do_store)

    async def create_collection(self, workspace: str, collection: str, metadata: dict):
        """Create a collection in Cassandra triple store via config push"""

        def _do_create():
            # Create or reuse connection for this workspace's keyspace
            if self.table is None or self.table != workspace:
                self.tg = None

                # Use factory function to select implementation
                KGClass = EntityCentricKnowledgeGraph

                try:
                    if self.cassandra_username and self.cassandra_password:
                        self.tg = KGClass(
                            hosts=self.cassandra_host,
                            keyspace=workspace,
                            username=self.cassandra_username,
                            password=self.cassandra_password,
                        )
                    else:
                        self.tg = KGClass(
                            hosts=self.cassandra_host,
                            keyspace=workspace,
                        )
                except Exception as e:
                    logger.error(f"Failed to connect to Cassandra for workspace {workspace}: {e}")
                    raise

                self.table = workspace

            # Create collection using the built-in method
            logger.info(f"Creating collection {collection} for workspace {workspace}")

            if self.tg.collection_exists(collection):
                logger.info(f"Collection {collection} already exists")
            else:
                self.tg.create_collection(collection)
                logger.info(f"Created collection {collection}")

        try:
            await asyncio.to_thread(_do_create)
        except Exception as e:
            logger.error(f"Failed to create collection {workspace}/{collection}: {e}", exc_info=True)
            raise

    async def delete_collection(self, workspace: str, collection: str):
        """Delete all data for a specific collection from the unified triples table"""

        def _do_delete():
            # Create or reuse connection for this workspace's keyspace
            if self.table is None or self.table != workspace:
                self.tg = None

                # Use factory function to select implementation
                KGClass = EntityCentricKnowledgeGraph

                try:
                    if self.cassandra_username and self.cassandra_password:
                        self.tg = KGClass(
                            hosts=self.cassandra_host,
                            keyspace=workspace,
                            username=self.cassandra_username,
                            password=self.cassandra_password,
                        )
                    else:
                        self.tg = KGClass(
                            hosts=self.cassandra_host,
                            keyspace=workspace,
                        )
                except Exception as e:
                    logger.error(f"Failed to connect to Cassandra for workspace {workspace}: {e}")
                    raise

                self.table = workspace

            # Delete all triples for this collection using the built-in method
            self.tg.delete_collection(collection)
            logger.info(f"Deleted all triples for collection {collection} from keyspace {workspace}")

        try:
            await asyncio.to_thread(_do_delete)
        except Exception as e:
            logger.error(f"Failed to delete collection {workspace}/{collection}: {e}", exc_info=True)
            raise

    @staticmethod
    def add_args(parser):

        TriplesStoreService.add_args(parser)
        add_cassandra_args(parser)

def run():

    Processor.launch(default_ident, __doc__)

