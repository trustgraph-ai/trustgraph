
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
from .... base import TriplesStoreService
from .... base import AsyncProcessor, Consumer, Producer
from .... base import ConsumerMetrics, ProducerMetrics
from .... base.cassandra_config import add_cassandra_args, resolve_cassandra_config
from .... schema import StorageManagementRequest, StorageManagementResponse, Error
from .... schema import triples_storage_management_topic, storage_management_response_topic

# Module logger
logger = logging.getLogger(__name__)

default_ident = "triples-write"


class Processor(TriplesStoreService):

    def __init__(self, **params):
        
        id = params.get("id", default_ident)

        # Get Cassandra parameters
        cassandra_host = params.get("cassandra_host")
        cassandra_username = params.get("cassandra_username")
        cassandra_password = params.get("cassandra_password")

        # Resolve configuration with environment variable fallback
        hosts, username, password = resolve_cassandra_config(
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

    async def start(self):
        """Start the processor and its storage management consumer"""
        await super().start()
        await self.storage_request_consumer.start()
        await self.storage_response_producer.start()

    async def on_storage_management(self, message):
        """Handle storage management requests"""
        logger.info(f"Storage management request: {message.operation} for {message.user}/{message.collection}")

        try:
            if message.operation == "delete-collection":
                await self.handle_delete_collection(message)
            else:
                response = StorageManagementResponse(
                    error=Error(
                        type="invalid_operation",
                        message=f"Unknown operation: {message.operation}"
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

    async def handle_delete_collection(self, message):
        """Delete all data for a specific collection from the unified triples table"""
        try:
            # Create or reuse connection for this user's keyspace
            if self.table is None or self.table != message.user:
                self.tg = None

                try:
                    if self.cassandra_username and self.cassandra_password:
                        self.tg = KnowledgeGraph(
                            hosts=self.cassandra_host,
                            keyspace=message.user,
                            username=self.cassandra_username,
                            password=self.cassandra_password
                        )
                    else:
                        self.tg = KnowledgeGraph(
                            hosts=self.cassandra_host,
                            keyspace=message.user,
                        )
                except Exception as e:
                    logger.error(f"Failed to connect to Cassandra for user {message.user}: {e}")
                    raise

                self.table = message.user

            # Delete all triples for this collection from the unified table
            # In the unified table schema, collection is the partition key
            delete_cql = """
                DELETE FROM triples
                WHERE collection = ?
            """

            try:
                self.tg.session.execute(delete_cql, (message.collection,))
                logger.info(f"Deleted all triples for collection {message.collection} from keyspace {message.user}")
            except Exception as e:
                logger.error(f"Failed to delete collection data: {e}")
                raise

            # Send success response
            response = StorageManagementResponse(
                error=None  # No error means success
            )
            await self.storage_response_producer.send(response)
            logger.info(f"Successfully deleted collection {message.user}/{message.collection}")

        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")
            raise

    @staticmethod
    def add_args(parser):

        TriplesStoreService.add_args(parser)
        add_cassandra_args(parser)

def run():

    Processor.launch(default_ident, __doc__)

