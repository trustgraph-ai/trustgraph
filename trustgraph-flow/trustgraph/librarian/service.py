
"""
Librarian service, manages documents in collections
"""

from functools import partial
import asyncio
import threading
import queue
import base64

from pulsar.schema import JsonSchema

from .. schema import LibrarianRequest, LibrarianResponse, Error
from .. schema import librarian_request_queue, librarian_response_queue

from .. schema import GraphEmbeddings
from .. schema import graph_embeddings_store_queue
from .. schema import Triples
from .. schema import triples_store_queue
from .. schema import DocumentEmbeddings
from .. schema import document_embeddings_store_queue

from .. schema import Document, Metadata
from .. schema import document_ingest_queue
from .. schema import TextDocument, Metadata
from .. schema import text_ingest_queue

from .. base import Publisher
from .. base import Subscriber

from .. log_level import LogLevel
from .. base import ConsumerProducer
from .. exceptions import RequestError

from . librarian import Librarian

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = librarian_request_queue
default_output_queue = librarian_response_queue
default_subscriber = module
default_minio_host = "minio:9000"
default_minio_access_key = "minioadmin"
default_minio_secret_key = "minioadmin"
default_cassandra_host = "cassandra"

bucket_name = "library"

# FIXME: How to ensure this doesn't conflict with other usage?
keyspace = "librarian"

class Processor(ConsumerProducer):

    def __init__(self, **params):

        self.running = True

        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)

        minio_host = params.get("minio_host", default_minio_host)
        minio_access_key = params.get(
            "minio_access_key",
            default_minio_access_key
        )
        minio_secret_key = params.get(
            "minio_secret_key",
            default_minio_secret_key
        )

        cassandra_host = params.get("cassandra_host", default_cassandra_host)
        cassandra_user = params.get("cassandra_user")
        cassandra_password = params.get("cassandra_password")

        triples_queue = params.get("triples_queue")
        graph_embeddings_queue = params.get("graph_embeddings_queue")
        document_embeddings_queue = params.get("document_embeddings_queue")
        document_load_queue = params.get("document_load_queue")
        text_load_queue = params.get("text_load_queue")

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "output_queue": output_queue,
                "subscriber": subscriber,
                "input_schema": LibrarianRequest,
                "output_schema": LibrarianResponse,
                "minio_host": minio_host,
                "minio_access_key": minio_access_key,
                "cassandra_host": cassandra_host,
                "cassandra_user": cassandra_user,
            }
        )

        self.document_load = Publisher(
            self.client, document_load_queue, JsonSchema(Document),
        )

        self.text_load = Publisher(
            self.client, text_load_queue, JsonSchema(TextDocument),
        )

        self.triples_brk = Subscriber(
            self.client, triples_store_queue,
            "librarian", "librarian",
            schema=JsonSchema(Triples),
        )
        self.graph_embeddings_brk = Subscriber(
            self.client, graph_embeddings_store_queue,
            "librarian", "librarian",
            schema=JsonSchema(GraphEmbeddings),
        )
        self.document_embeddings_brk = Subscriber(
            self.client, document_embeddings_store_queue,
            "librarian", "librarian",
            schema=JsonSchema(DocumentEmbeddings),
        )

        self.triples_reader = threading.Thread(
            target=self.receive_triples
        )
        self.graph_embeddings_reader = threading.Thread(
            target=self.receive_graph_embeddings
        )
        self.document_embeddings_reader = threading.Thread(
            target=self.receive_document_embeddings
        )

        self.librarian = Librarian(
            cassandra_host = cassandra_host.split(","),
            cassandra_user = cassandra_user,
            cassandra_password = cassandra_password,
            minio_host = minio_host,
            minio_access_key = minio_access_key,
            minio_secret_key = minio_secret_key,
            bucket_name = bucket_name,
            keyspace = keyspace,
            load_document = self.load_document,
            load_text = self.load_text,
        )

        print("Initialised.", flush=True)

    async def start(self):
        
        self.document_load.start()
        self.text_load.start()

        self.triples_brk.start()
        self.graph_embeddings_brk.start()
        self.document_embeddings_brk.start()

        self.triples_sub = self.triples_brk.subscribe_all("x")
        self.graph_embeddings_sub = self.graph_embeddings_brk.subscribe_all("x")
        self.document_embeddings_sub = self.document_embeddings_brk.subscribe_all("x")

        self.triples_reader.start()
        self.graph_embeddings_reader.start()
        self.document_embeddings_reader.start()

    def __del__(self):

        self.running = False

        if hasattr(self, "document_load"):
            self.document_load.stop()
            self.document_load.join()

        if hasattr(self, "text_load"):
            self.text_load.stop()
            self.text_load.join()

        if hasattr(self, "triples_sub"):
            self.triples_sub.unsubscribe_all("x")

        if hasattr(self, "graph_embeddings_sub"):
            self.graph_embeddings_sub.unsubscribe_all("x")

        if hasattr(self, "document_embeddings_sub"):
            self.document_embeddings_sub.unsubscribe_all("x")

        if hasattr(self, "triples_brk"):
            self.triples_brk.stop()
            self.triples_brk.join()

        if hasattr(self, "graph_embeddings_brk"):
            self.graph_embeddings_brk.stop()
            self.graph_embeddings_brk.join()

        if hasattr(self, "document_embeddings_brk"):
            self.document_embeddings_brk.stop()
            self.document_embeddings_brk.join()

    def receive_triples(self):

        while self.running:
            try:
                msg = self.triples_sub.get(timeout=1)
            except queue.Empty:
                continue

            self.librarian.handle_triples(msg)

    def receive_graph_embeddings(self):

        while self.running:
            try:
                msg = self.graph_embeddings_sub.get(timeout=1)
            except queue.Empty:
                continue

            self.librarian.handle_graph_embeddings(msg)

    def receive_document_embeddings(self):

        while self.running:
            try:
                msg = self.document_embeddings_sub.get(timeout=1)
            except queue.Empty:
                continue

            self.librarian.handle_document_embeddings(msg)

    async def load_document(self, document):

        doc = Document(
            metadata = Metadata(
                id = document.id,
                metadata = document.metadata,
                user = document.user,
                collection = document.collection
            ),
            data = document.document
        )

        self.document_load.send(None, doc)

    async def load_text(self, document):

        text = base64.b64decode(document.document)
        text = text.decode("utf-8")

        doc = TextDocument(
            metadata = Metadata(
                id = document.id,
                metadata = document.metadata,
                user = document.user,
                collection = document.collection
            ),
            text = text,
        )

        self.text_load.send(None, doc)

    def parse_request(self, v):

        if v.operation is None:
            raise RequestError("Null operation")

        print("op", v.operation)

        if v.operation == "add":
            if (
                    v.document and v.document.id and v.document.metadata and
                    v.document.document and v.document.kind
            ):
                return partial(
                    self.librarian.add,
                    document = v.document,
                )
            else:
                raise RequestError("Invalid call")

        if v.operation == "list":
            print("list", v)
            print(v.user)
            if v.user:
                return partial(
                    self.librarian.list,
                    user = v.user,
                    collection = v.collection,
                )
            else:
                print("BROK")
                raise RequestError("Invalid call")

        raise RequestError("Invalid operation: " + v.operation)

    async def handle(self, msg):

        v = msg.value()

        # Sender-produced ID

        id = msg.properties()["id"]

        print(f"Handling input {id}...", flush=True)

        try:
            func = self.parse_request(v)
        except RequestError as e:
            resp = LibrarianResponse(
                error = Error(
                    type = "request-error",
                    message = str(e),
                )
            )
            await self.send(resp, properties={"id": id})
            return

        try:
            resp = await func()
            print("->", resp)
        except RequestError as e:
            resp = LibrarianResponse(
                error = Error(
                    type = "request-error",
                    message = str(e),
                )
            )
            await self.send(resp, properties={"id": id})
            return
        except Exception as e:
            print("Exception:", e, flush=True)
            resp = LibrarianResponse(
                error = Error(
                    type = "processing-error",
                    message = "Unhandled error: " + str(e),
                )
            )
            await self.send(resp, properties={"id": id})
            return

        print("Send response..!.", flush=True)

        await self.send(resp, properties={"id": id})

        print("Done.", flush=True)

    @staticmethod
    def add_args(parser):

        ConsumerProducer.add_args(
            parser, default_input_queue, default_subscriber,
            default_output_queue,
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

        parser.add_argument(
            '--cassandra-host',
            default="cassandra",
            help=f'Graph host (default: cassandra)'
        )

        parser.add_argument(
            '--cassandra-user',
            default=None,
            help=f'Cassandra user'
        )

        parser.add_argument(
            '--cassandra-password',
            default=None,
            help=f'Cassandra password'
        )

        parser.add_argument(
            '--triples-queue',
            default=triples_store_queue,
            help=f'Triples queue (default: {triples_store_queue})'
        )

        parser.add_argument(
            '--graph-embeddings-queue',
            default=graph_embeddings_store_queue,
            help=f'Graph embeddings queue (default: {triples_store_queue})'
        )

        parser.add_argument(
            '--document-embeddings-queue',
            default=document_embeddings_store_queue,
            help='Document embeddings queue '
            f'(default: {document_embeddings_store_queue})'
        )

        parser.add_argument(
            '--document-load-queue',
            default=document_ingest_queue,
            help='Document load queue '
            f'(default: {document_ingest_queue})'
        )

        parser.add_argument(
            '--text-load-queue',
            default=text_ingest_queue,
            help='Text ingest queue '
            f'(default: {text_ingest_queue})'
        )

def run():

    Processor.launch(module, __doc__)

