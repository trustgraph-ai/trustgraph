
"""
Librarian service, manages documents in collections
"""

from functools import partial
import asyncio
import base64
import json

from .. base import AsyncProcessor, Consumer, Producer, Publisher, Subscriber
from .. base import ConsumerMetrics, ProducerMetrics

from .. schema import LibrarianRequest, LibrarianResponse, Error
from .. schema import librarian_request_queue, librarian_response_queue

from .. schema import Document, Metadata
from .. schema import TextDocument, Metadata

from .. exceptions import RequestError

from . librarian import Librarian

default_ident = "librarian"

default_librarian_request_queue = librarian_request_queue
default_librarian_response_queue = librarian_response_queue

default_minio_host = "minio:9000"
default_minio_access_key = "minioadmin"
default_minio_secret_key = "minioadmin"
default_cassandra_host = "cassandra"

bucket_name = "library"

# FIXME: How to ensure this doesn't conflict with other usage?
keyspace = "librarian"

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

        super(Processor, self).__init__(
            **params | {
                "librarian_request_queue": librarian_request_queue,
                "librarian_response_queue": librarian_response_queue,
                "minio_host": minio_host,
                "minio_access_key": minio_access_key,
                "cassandra_host": cassandra_host,
                "cassandra_user": cassandra_user,
            }
        )

        librarian_request_metrics = ConsumerMetrics(
            processor = self.id, flow = None, name = "librarian-request"
        )

        librarian_response_metrics = ProducerMetrics(
            processor = self.id, flow = None, name = "librarian-response"
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

        self.register_config_handler(self.on_librarian_config)

        self.flows = {}

        print("Initialised.", flush=True)

    async def start(self):

        await super(Processor, self).start()
        await self.librarian_request_consumer.start()
        await self.librarian_response_producer.start()

    async def on_librarian_config(self, config, version):

        print("config version", version)

        if "flows" in config:

            self.flows = {
                k: json.loads(v)
                for k, v in config["flows"].items()
            }

        print(self.flows)

    def __del__(self):

        pass

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

    async def process_request(self, v):

        if v.operation is None:
            raise RequestError("Null operation")

        print("requets", v.operation)

        impls = {
            "add-document": self.librarian.add_document,
            "remove-document": self.librarian.remove_document,
            "update-document": self.librarian.update_document,
            "get-document-metadata": self.librarian.get_document_metadata,
            "get-document-content": self.librarian.get_document_content,
            "add-processing": self.librarian.add_processing,
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

        print(f"Handling input {id}...", flush=True)

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

        print("Done.", flush=True)

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

def run():

    Processor.launch(default_ident, __doc__)

