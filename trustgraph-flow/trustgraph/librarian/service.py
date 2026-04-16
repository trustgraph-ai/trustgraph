
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
from .. schema import Triples

from .. exceptions import RequestError

from .. provenance import (
    document_uri, document_triples, get_vocabulary_triples,
)

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

default_object_store_endpoint = "ceph-rgw:7480"
default_object_store_access_key = "object-user"
default_object_store_secret_key = "object-password"
default_object_store_use_ssl = False
default_object_store_region = None
default_cassandra_host = "cassandra"
default_min_chunk_size = 1  # No minimum by default (for Garage)

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

        object_store_endpoint = params.get("object_store_endpoint", default_object_store_endpoint)
        object_store_access_key = params.get(
            "object_store_access_key",
            default_object_store_access_key
        )
        object_store_secret_key = params.get(
            "object_store_secret_key",
            default_object_store_secret_key
        )
        object_store_use_ssl = params.get(
            "object_store_use_ssl",
            default_object_store_use_ssl
        )
        object_store_region = params.get(
            "object_store_region",
            default_object_store_region
        )

        min_chunk_size = params.get(
            "min_chunk_size",
            default_min_chunk_size
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
                "object_store_endpoint": object_store_endpoint,
                "object_store_access_key": object_store_access_key,
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

        self.librarian_request_topic = librarian_request_queue
        self.librarian_request_subscriber = id

        self.librarian_request_consumer = Consumer(
            taskgroup = self.taskgroup,
            backend = self.pubsub,
            flow = None,
            topic = librarian_request_queue,
            subscriber = id,
            schema = LibrarianRequest,
            handler = self.on_librarian_request,
            metrics = librarian_request_metrics,
        )

        self.librarian_response_producer = Producer(
            backend = self.pubsub,
            topic = librarian_response_queue,
            schema = LibrarianResponse,
            metrics = librarian_response_metrics,
        )

        self.collection_request_topic = collection_request_queue
        self.collection_request_subscriber = id

        self.collection_request_consumer = Consumer(
            taskgroup = self.taskgroup,
            backend = self.pubsub,
            flow = None,
            topic = collection_request_queue,
            subscriber = id,
            schema = CollectionManagementRequest,
            handler = self.on_collection_request,
            metrics = collection_request_metrics,
        )

        self.collection_response_producer = Producer(
            backend = self.pubsub,
            topic = collection_response_queue,
            schema = CollectionManagementResponse,
            metrics = collection_response_metrics,
        )

        # Config service client for collection management
        config_request_metrics = ProducerMetrics(
            processor = id, flow = None, name = "config-request"
        )

        self.config_request_producer = Producer(
            backend = self.pubsub,
            topic = config_request_queue,
            schema = ConfigRequest,
            metrics = config_request_metrics,
        )

        config_response_metrics = ConsumerMetrics(
            processor = id, flow = None, name = "config-response"
        )

        self.config_response_consumer = Consumer(
            taskgroup = self.taskgroup,
            backend = self.pubsub,
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
            object_store_endpoint = object_store_endpoint,
            object_store_access_key = object_store_access_key,
            object_store_secret_key = object_store_secret_key,
            bucket_name = bucket_name,
            keyspace = keyspace,
            load_document = self.load_document,
            object_store_use_ssl = object_store_use_ssl,
            object_store_region = object_store_region,
            min_chunk_size = min_chunk_size,
        )

        self.collection_manager = CollectionManager(
            config_request_producer = self.config_request_producer,
            config_response_consumer = self.config_response_consumer,
            taskgroup = self.taskgroup,
        )

        self.register_config_handler(
            self.on_librarian_config,
            types=["flow"],
        )

        self.flows = {}

        logger.info("Librarian service initialized")

    async def start(self):

        await self.pubsub.ensure_queue(
            self.librarian_request_topic, self.librarian_request_subscriber
        )
        await self.pubsub.ensure_queue(
            self.collection_request_topic, self.collection_request_subscriber
        )
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

        if "flow" in config:

            self.flows = {
                k: json.loads(v)
                for k, v in config["flow"].items()
            }

        logger.debug(f"Flows: {self.flows}")

    def __del__(self):

        pass

    # Threshold for sending document_id instead of inline content (2MB)

    async def emit_document_provenance(self, document, processing, triples_queue):
        """
        Emit document provenance metadata to the knowledge graph.

        This emits:
        1. Vocabulary bootstrap triples (idempotent, safe to re-emit)
        2. Document metadata as PROV-O triples
        """
        logger.debug(f"Emitting document provenance for {document.id}")

        # Build document URI and provenance triples
        doc_uri = document_uri(document.id)

        # Get page count for PDFs (if available from document metadata)
        page_count = None
        if document.kind == "application/pdf":
            # Page count might be in document metadata triples
            # For now, we don't have it at this point - it gets determined during extraction
            pass

        # Build document metadata triples
        prov_triples = document_triples(
            doc_uri=doc_uri,
            title=document.title if document.title else None,
            mime_type=document.kind,
        )

        # Include any existing metadata triples from the document
        if document.metadata:
            prov_triples.extend(document.metadata)

        # Get vocabulary bootstrap triples (idempotent)
        vocab_triples = get_vocabulary_triples()

        # Combine all triples
        all_triples = vocab_triples + prov_triples

        # Create publisher and emit
        triples_pub = Publisher(
            self.pubsub, triples_queue, schema=Triples
        )

        try:
            await triples_pub.start()

            triples_msg = Triples(
                metadata=Metadata(
                    id=doc_uri,
                    root=document.id,
                    user=processing.user,
                    collection=processing.collection,
                ),
                triples=all_triples,
            )

            await triples_pub.send(None, triples_msg)
            logger.debug(f"Emitted {len(all_triples)} provenance triples for {document.id}")

        finally:
            await triples_pub.stop()

    async def load_document(self, document, processing, content):

        logger.debug("Ready for document processing...")

        logger.debug(f"Document: {document}, processing: {processing}, content length: {len(content)}")

        if processing.flow not in self.flows:
            raise RuntimeError("Invalid flow ID")

        flow = self.flows[processing.flow]

        if document.kind == "text/plain":
            kind = "text-load"
        else:
            kind = "document-load"

        q = flow["interfaces"][kind]["flow"]

        # Emit document provenance to knowledge graph
        if "triples-store" in flow["interfaces"]:
            await self.emit_document_provenance(
                document, processing, flow["interfaces"]["triples-store"]["flow"]
            )

        if kind == "text-load":
            doc = TextDocument(
                metadata = Metadata(
                    id = document.id,
                    root = document.id,
                    user = processing.user,
                    collection = processing.collection
                ),
                document_id = document.id,
                text = b"",
            )
            schema = TextDocument
        else:
            doc = Document(
                metadata = Metadata(
                    id = document.id,
                    root = document.id,
                    user = processing.user,
                    collection = processing.collection
                ),
                document_id = document.id,
                data = b"",
            )
            schema = Document

        logger.debug(f"Submitting to queue {q}...")

        pub = Publisher(
            self.pubsub, q, schema=schema
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
            # Chunked upload operations
            "begin-upload": self.librarian.begin_upload,
            "upload-chunk": self.librarian.upload_chunk,
            "complete-upload": self.librarian.complete_upload,
            "abort-upload": self.librarian.abort_upload,
            "get-upload-status": self.librarian.get_upload_status,
            "list-uploads": self.librarian.list_uploads,
            # Child document and streaming operations
            "add-child-document": self.librarian.add_child_document,
            "list-children": self.librarian.list_children,
            "stream-document": self.librarian.stream_document,
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

            # Handle streaming operations specially
            if v.operation == "stream-document":
                async for resp in self.librarian.stream_document(v):
                    await self.librarian_response_producer.send(
                        resp, properties={"id": id}
                    )
                return

            # Non-streaming operations
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
                ),
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
                ),
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
            '--object-store-endpoint',
            default=default_object_store_endpoint,
            help=f'Object storage endpoint (default: {default_object_store_endpoint})',
        )

        parser.add_argument(
            '--object-store-access-key',
            default=default_object_store_access_key,
            help='Object storage access key / username '
            f'(default: {default_object_store_access_key})',
        )

        parser.add_argument(
            '--object-store-secret-key',
            default=default_object_store_secret_key,
            help='Object storage secret key / password '
            f'(default: {default_object_store_secret_key})',
        )

        parser.add_argument(
            '--object-store-use-ssl',
            action='store_true',
            default=default_object_store_use_ssl,
            help=f'Use SSL/TLS for object storage connection (default: {default_object_store_use_ssl})',
        )

        parser.add_argument(
            '--object-store-region',
            default=default_object_store_region,
            help='Object storage region (optional)',
        )

        parser.add_argument(
            '--min-chunk-size',
            type=int,
            default=default_min_chunk_size,
            help=f'Minimum chunk size in bytes for uploads/downloads '
            f'(default: {default_min_chunk_size})',
        )

        add_cassandra_args(parser)

def run():

    Processor.launch(default_ident, __doc__)

