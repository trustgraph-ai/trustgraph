
"""
Librarian service, manages documents in collections
"""

from functools import partial
import asyncio
import base64
import json
import logging
from datetime import datetime

from .. base import AsyncProcessor, Consumer, Producer, Publisher, Subscriber
from .. base import ConsumerMetrics, ProducerMetrics
from .. base.cassandra_config import add_cassandra_args, resolve_cassandra_config

from .. schema import LibrarianRequest, LibrarianResponse, Error
from .. schema import librarian_request_queue, librarian_response_queue
from .. schema import CollectionManagementRequest, CollectionManagementResponse
from .. schema import collection_request_queue, collection_response_queue
from .. schema import ConfigRequest, ConfigResponse
from .. schema import config_request_queue, config_response_queue

from .. schema import Document, Metadata
from .. schema import TextDocument, Metadata

from .. exceptions import RequestError

from . librarian import Librarian
from . collection_manager import CollectionManager

# Module logger
logger = logging.getLogger(__name__)

default_ident = "librarian"

default_librarian_request_queue = librarian_request_queue
default_librarian_response_queue = librarian_response_queue
default_collection_request_queue = collection_request_queue
default_collection_response_queue = collection_response_queue
default_config_request_queue = config_request_queue
default_config_response_queue = config_response_queue

default_minio_host = "minio:9000"
default_minio_access_key = "minioadmin"
default_minio_secret_key = "minioadmin"
default_cassandra_host = "cassandra"

bucket_name = "library"

class Processor(AsyncProcessor):

    def __init__(self, **params):

        id = params.get("id")

#        self.running = True

        librarian_request_queue = params.get(
            "librarian_request_queue", default_librarian_request_queue
        )

        librarian_response_queue = params.get(
            "librarian_response_queue", default_librarian_response_queue
        )

        collection_request_queue = params.get(
            "collection_request_queue", default_collection_request_queue
        )

        collection_response_queue = params.get(
            "collection_response_queue", default_collection_response_queue
        )

        config_request_queue = params.get(
            "config_request_queue", default_config_request_queue
        )

        config_response_queue = params.get(
            "config_response_queue", default_config_response_queue
        )

        minio_host = params.get("minio_host", default_minio_host)
        minio_access_key = params.get(
            "minio_access_key",
            default_minio_access_key
        )
        minio_secret_key = params.get(
            "minio_secret_key",
            default_minio_secret_key
        )

        cassandra_host = params.get("cassandra_host")
        cassandra_username = params.get("cassandra_username")
        cassandra_password = params.get("cassandra_password")

        # Resolve configuration with environment variable fallback
        hosts, username, password, keyspace = resolve_cassandra_config(
            host=cassandra_host,
            username=cassandra_username,
            password=cassandra_password,
            default_keyspace="librarian"
        )

        # Store resolved configuration
        self.cassandra_host = hosts
        self.cassandra_username = username
        self.cassandra_password = password

        super(Processor, self).__init__(
            **params | {
                "librarian_request_queue": librarian_request_queue,
                "librarian_response_queue": librarian_response_queue,
                "collection_request_queue": collection_request_queue,
                "collection_response_queue": collection_response_queue,
                "minio_host": minio_host,
                "minio_access_key": minio_access_key,
                "cassandra_host": self.cassandra_host,
                "cassandra_username": self.cassandra_username,
                "cassandra_password": self.cassandra_password,
            }
        )

        librarian_request_metrics = ConsumerMetrics(
            processor = self.id, flow = None, name = "librarian-request"
        )

        librarian_response_metrics = ProducerMetrics(
            processor = self.id, flow = None, name = "librarian-response"
        )

        collection_request_metrics = ConsumerMetrics(
            processor = self.id, flow = None, name = "collection-request"
        )

        collection_response_metrics = ProducerMetrics(
            processor = self.id, flow = None, name = "collection-response"
        )

        storage_response_metrics = ConsumerMetrics(
            processor = self.id, flow = None, name = "storage-response"
        )

        self.librarian_request_consumer = Consumer(
            taskgroup = self.taskgroup,
            client = self.pulsar_client,
            flow = None,
            topic = librarian_request_queue,
            subscriber = id,
            schema = LibrarianRequest,
            handler = self.on_librarian_request,
            metrics = librarian_request_metrics,
        )

        self.librarian_response_producer = Producer(
            client = self.pulsar_client,
            topic = librarian_response_queue,
            schema = LibrarianResponse,
            metrics = librarian_response_metrics,
        )

        self.collection_request_consumer = Consumer(
            taskgroup = self.taskgroup,
            client = self.pulsar_client,
            flow = None,
            topic = collection_request_queue,
            subscriber = id,
            schema = CollectionManagementRequest,
            handler = self.on_collection_request,
            metrics = collection_request_metrics,
        )

        self.collection_response_producer = Producer(
            client = self.pulsar_client,
            topic = collection_response_queue,
            schema = CollectionManagementResponse,
            metrics = collection_response_metrics,
        )

        # Config service client for collection management
        config_request_metrics = ProducerMetrics(
            processor = id, flow = None, name = "config-request"
        )

        self.config_request_producer = Producer(
            client = self.pulsar_client,
            topic = config_request_queue,
            schema = ConfigRequest,
            metrics = config_request_metrics,
        )

        config_response_metrics = ConsumerMetrics(
            processor = id, flow = None, name = "config-response"
        )

        self.config_response_consumer = Consumer(
            taskgroup = self.taskgroup,
            client = self.pulsar_client,
            flow = None,
            topic = config_response_queue,
            subscriber = f"{id}-config",
            schema = ConfigResponse,
            handler = self.on_config_response,
            metrics = config_response_metrics,
        )

        self.librarian = Librarian(
            cassandra_host = self.cassandra_host,
            cassandra_username = self.cassandra_username,
            cassandra_password = self.cassandra_password,
            minio_host = minio_host,
            minio_access_key = minio_access_key,
            minio_secret_key = minio_secret_key,
            bucket_name = bucket_name,
            keyspace = keyspace,
            load_document = self.load_document,
        )

        self.collection_manager = CollectionManager(
            config_request_producer = self.config_request_producer,
            config_response_consumer = self.config_response_consumer,
            taskgroup = self.taskgroup,
        )

        self.register_config_handler(self.on_librarian_config)

        self.flows = {}

        logger.info("Librarian service initialized")

    async def start(self):

        await super(Processor, self).start()
        await self.librarian_request_consumer.start()
        await self.librarian_response_producer.start()
        await self.collection_request_consumer.start()
        await self.collection_response_producer.start()
        await self.config_request_producer.start()
        await self.config_response_consumer.start()

    async def on_config_response(self, message, consumer, flow):
        """Forward config responses to collection manager"""
        await self.collection_manager.on_config_response(message, consumer, flow)

    async def on_librarian_config(self, config, version):

        logger.info(f"Configuration version: {version}")

        if "flows" in config:

            self.flows = {
                k: json.loads(v)
                for k, v in config["flows"].items()
            }

        logger.debug(f"Flows: {self.flows}")

    def __del__(self):

        pass

    async def load_document(self, document, processing, content):

        logger.debug("Ready for document processing...")

        logger.debug(f"Document: {document}, processing: {processing}, content length: {len(content)}")

        if processing.flow not in self.flows:
            raise RuntimeError("Invalid flow ID")

        flow = self.flows[processing.flow]

        if document.kind == "text/plain":
            kind = "text-load"
        elif document.kind == "application/pdf":
            kind = "document-load"
        else:
            raise RuntimeError("Document with a MIME type I don't know")

        q = flow["interfaces"][kind]

        if kind == "text-load":
            doc = TextDocument(
                metadata = Metadata(
                    id = document.id,
                    metadata = document.metadata,
                    user = processing.user,
                    collection = processing.collection
                ),
                text = content,
            )
            schema = TextDocument
        else:
            doc = Document(
                metadata = Metadata(
                    id = document.id,
                    metadata = document.metadata,
                    user = processing.user,
                    collection = processing.collection
                ),
                data = base64.b64encode(content).decode("utf-8")

            )
            schema = Document

        logger.debug(f"Submitting to queue {q}...")

        pub = Publisher(
            self.pulsar_client, q, schema=schema
        )

        await pub.start()

        # FIXME: Time wait kludge?
        await asyncio.sleep(1)

        await pub.send(None, doc)

        await pub.stop()

        logger.debug("Document submitted")

    async def add_processing_with_collection(self, request):
        """
        Wrapper for add_processing that ensures collection exists
        """
        # Ensure collection exists when processing is added
        if hasattr(request, 'processing_metadata') and request.processing_metadata:
            user = request.processing_metadata.user
            collection = request.processing_metadata.collection
            await self.collection_manager.ensure_collection_exists(user, collection)

        # Call the original add_processing method
        return await self.librarian.add_processing(request)

    async def process_request(self, v):

        if v.operation is None:
            raise RequestError("Null operation")

        logger.debug(f"Librarian request: {v.operation}")

        impls = {
            "add-document": self.librarian.add_document,
            "remove-document": self.librarian.remove_document,
            "update-document": self.librarian.update_document,
            "get-document-metadata": self.librarian.get_document_metadata,
            "get-document-content": self.librarian.get_document_content,
            "add-processing": self.add_processing_with_collection,
            "remove-processing": self.librarian.remove_processing,
            "list-documents": self.librarian.list_documents,
            "list-processing": self.librarian.list_processing,
        }

        if v.operation not in impls:
            raise RequestError(f"Invalid operation: {v.operation}")

        return await impls[v.operation](v)

    async def on_librarian_request(self, msg, consumer, flow):

        v = msg.value()

        # Sender-produced ID

        id = msg.properties()["id"]

        logger.info(f"Handling librarian input {id}...")

        try:

            resp = await self.process_request(v)

            await self.librarian_response_producer.send(
                resp, properties={"id": id}
            )

            return

        except RequestError as e:
            resp = LibrarianResponse(
                error = Error(
                    type = "request-error",
                    message = str(e),
                )
            )

            await self.librarian_response_producer.send(
                resp, properties={"id": id}
            )

            return
        except Exception as e:
            resp = LibrarianResponse(
                error = Error(
                    type = "unexpected-error",
                    message = str(e),
                )
            )

            await self.librarian_response_producer.send(
                resp, properties={"id": id}
            )

            return

        logger.debug("Librarian input processing complete")

    async def process_collection_request(self, v):
        """
        Process collection management requests
        """
        if v.operation is None:
            raise RequestError("Null operation")

        logger.debug(f"Collection request: {v.operation}")

        impls = {
            "list-collections": self.collection_manager.list_collections,
            "update-collection": self.collection_manager.update_collection,
            "delete-collection": self.collection_manager.delete_collection,
        }

        if v.operation not in impls:
            raise RequestError(f"Invalid collection operation: {v.operation}")

        return await impls[v.operation](v)

    async def on_collection_request(self, msg, consumer, flow):
        """
        Handle collection management request messages
        """
        v = msg.value()
        id = msg.properties().get("id", "unknown")

        logger.info(f"Handling collection request {id}...")

        try:
            resp = await self.process_collection_request(v)
            await self.collection_response_producer.send(
                resp, properties={"id": id}
            )
        except RequestError as e:
            resp = CollectionManagementResponse(
                error=Error(
                    type="request-error",
                    message=str(e),
                ),
                timestamp=datetime.now().isoformat()
            )
            await self.collection_response_producer.send(
                resp, properties={"id": id}
            )
        except Exception as e:
            resp = CollectionManagementResponse(
                error=Error(
                    type="unexpected-error",
                    message=str(e),
                ),
                timestamp=datetime.now().isoformat()
            )
            await self.collection_response_producer.send(
                resp, properties={"id": id}
            )

        logger.debug("Collection request processing complete")

    @staticmethod
    def add_args(parser):

        AsyncProcessor.add_args(parser)

        parser.add_argument(
            '--librarian-request-queue',
            default=default_librarian_request_queue,
            help=f'Config request queue (default: {default_librarian_request_queue})'
        )

        parser.add_argument(
            '--librarian-response-queue',
            default=default_librarian_response_queue,
            help=f'Config response queue {default_librarian_response_queue}',
        )

        parser.add_argument(
            '--collection-request-queue',
            default=default_collection_request_queue,
            help=f'Collection request queue (default: {default_collection_request_queue})'
        )

        parser.add_argument(
            '--collection-response-queue',
            default=default_collection_response_queue,
            help=f'Collection response queue (default: {default_collection_response_queue})'
        )

        parser.add_argument(
            '--minio-host',
            default=default_minio_host,
            help=f'Minio hostname (default: {default_minio_host})',
        )

        parser.add_argument(
            '--minio-access-key',
            default='minioadmin',
            help='Minio access key / username '
            f'(default: {default_minio_access_key})',
        )

        parser.add_argument(
            '--minio-secret-key',
            default='minioadmin',
            help='Minio secret key / password '
            f'(default: {default_minio_access_key})',
        )

        add_cassandra_args(parser)

def run():

    Processor.launch(default_ident, __doc__)

