
"""
Graph writer.  Input is graph edge.  Writes edges to Cassandra graph.
"""

import pulsar
import base64
import os
import argparse
import time
import logging

from .... direct.cassandra_kg import KnowledgeGraph
from .... base import TriplesStoreService, CollectionConfigHandler
from .... base import AsyncProcessor, Consumer, Producer
from .... base import ConsumerMetrics, ProducerMetrics
from .... base.cassandra_config import add_cassandra_args, resolve_cassandra_config

# Module logger
logger = logging.getLogger(__name__)

default_ident = "triples-write"


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
        self.register_config_handler(self.on_collection_config)

    async def store_triples(self, message):

        user = message.metadata.user

        if self.table is None or self.table != user:

            self.tg = None

            try:
                if self.cassandra_username and self.cassandra_password:
                    self.tg = KnowledgeGraph(
                        hosts=self.cassandra_host,
                        keyspace=message.metadata.user,
                        username=self.cassandra_username, password=self.cassandra_password
                    )
                else:
                    self.tg = KnowledgeGraph(
                        hosts=self.cassandra_host,
                        keyspace=message.metadata.user,
                    )
            except Exception as e:
                logger.error(f"Exception: {e}", exc_info=True)
                time.sleep(1)
                raise e

            self.table = user

        for t in message.triples:
            self.tg.insert(
                message.metadata.collection,
                t.s.value,
                t.p.value,
                t.o.value
            )

    async def create_collection(self, user: str, collection: str, metadata: dict):
        """Create a collection in Cassandra triple store via config push"""
        try:
            # Create or reuse connection for this user's keyspace
            if self.table is None or self.table != user:
                self.tg = None

                try:
                    if self.cassandra_username and self.cassandra_password:
                        self.tg = KnowledgeGraph(
                            hosts=self.cassandra_host,
                            keyspace=user,
                            username=self.cassandra_username,
                            password=self.cassandra_password
                        )
                    else:
                        self.tg = KnowledgeGraph(
                            hosts=self.cassandra_host,
                            keyspace=user,
                        )
                except Exception as e:
                    logger.error(f"Failed to connect to Cassandra for user {user}: {e}")
                    raise

                self.table = user

            # Create collection using the built-in method
            logger.info(f"Creating collection {collection} for user {user}")

            if self.tg.collection_exists(collection):
                logger.info(f"Collection {collection} already exists")
            else:
                self.tg.create_collection(collection)
                logger.info(f"Created collection {collection}")

        except Exception as e:
            logger.error(f"Failed to create collection {user}/{collection}: {e}", exc_info=True)
            raise

    async def delete_collection(self, user: str, collection: str):
        """Delete all data for a specific collection from the unified triples table"""
        try:
            # Create or reuse connection for this user's keyspace
            if self.table is None or self.table != user:
                self.tg = None

                try:
                    if self.cassandra_username and self.cassandra_password:
                        self.tg = KnowledgeGraph(
                            hosts=self.cassandra_host,
                            keyspace=user,
                            username=self.cassandra_username,
                            password=self.cassandra_password
                        )
                    else:
                        self.tg = KnowledgeGraph(
                            hosts=self.cassandra_host,
                            keyspace=user,
                        )
                except Exception as e:
                    logger.error(f"Failed to connect to Cassandra for user {user}: {e}")
                    raise

                self.table = user

            # Delete all triples for this collection using the built-in method
            self.tg.delete_collection(collection)
            logger.info(f"Deleted all triples for collection {collection} from keyspace {user}")

        except Exception as e:
            logger.error(f"Failed to delete collection {user}/{collection}: {e}", exc_info=True)
            raise

    @staticmethod
    def add_args(parser):

        TriplesStoreService.add_args(parser)
        add_cassandra_args(parser)

def run():

    Processor.launch(default_ident, __doc__)

