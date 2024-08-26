
"""
Simple RAG service, performs query using document RAG an LLM.
Input is query, output is response.
"""

from ... schema import DocumentRagQuery, DocumentRagResponse, Error
from ... schema import document_rag_request_queue, document_rag_response_queue
from ... schema import prompt_request_queue
from ... schema import prompt_response_queue
from ... schema import embeddings_request_queue
from ... schema import embeddings_response_queue
from ... schema import document_embeddings_request_queue
from ... schema import document_embeddings_response_queue
from ... log_level import LogLevel
from ... document_rag import DocumentRag
from ... base import ConsumerProducer

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = document_rag_request_queue
default_output_queue = document_rag_response_queue
default_subscriber = module

class Processor(ConsumerProducer):

    def __init__(self, **params):

        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)
        entity_limit = params.get("entity_limit", 50)
        triple_limit = params.get("triple_limit", 30)
        pr_request_queue = params.get(
            "prompt_request_queue", prompt_request_queue
        )
        pr_response_queue = params.get(
            "prompt_response_queue", prompt_response_queue
        )
        emb_request_queue = params.get(
            "embeddings_request_queue", embeddings_request_queue
        )
        emb_response_queue = params.get(
            "embeddings_response_queue", embeddings_response_queue
        )
        de_request_queue = params.get(
            "document_embeddings_request_queue",
            document_embeddings_request_queue
        )
        de_response_queue = params.get(
            "document_embeddings_response_queue",
            document_embeddings_response_queue
        )

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "output_queue": output_queue,
                "subscriber": subscriber,
                "input_schema": DocumentRagQuery,
                "output_schema": DocumentRagResponse,
                "prompt_request_queue": pr_request_queue,
                "prompt_response_queue": pr_response_queue,
                "embeddings_request_queue": emb_request_queue,
                "embeddings_response_queue": emb_response_queue,
                "document_embeddings_request_queue": de_request_queue,
                "document_embeddings_response_queue": de_response_queue,
            }
        )

        self.rag = DocumentRag(
            pulsar_host=self.pulsar_host,
            pr_request_queue=pr_request_queue,
            pr_response_queue=pr_response_queue,
            emb_request_queue=emb_request_queue,
            emb_response_queue=emb_response_queue,
            de_request_queue=de_request_queue,
            de_response_queue=de_response_queue,
            verbose=True,
            module=module,
        )

    def handle(self, msg):

        try:

            v = msg.value()

            # Sender-produced ID
            id = msg.properties()["id"]

            print(f"Handling input {id}...", flush=True)

            response = self.rag.query(v.query)

            print("Send response...", flush=True)
            r = DocumentRagResponse(response = response, error=None)
            self.producer.send(r, properties={"id": id})

            print("Done.", flush=True)

        except Exception as e:

            print(f"Exception: {e}")

            print("Send error response...", flush=True)

            r = GraphRagResponse(
                error=Error(
                    type = "llm-error",
                    message = str(e),
                ),
                response=None,
            )

            self.producer.send(r, properties={"id": id})

            self.consumer.acknowledge(msg)

    @staticmethod
    def add_args(parser):

        ConsumerProducer.add_args(
            parser, default_input_queue, default_subscriber,
            default_output_queue,
        )

        parser.add_argument(
            '-v', '--vector-store',
            default='http://milvus:19530',
            help=f'Vector host (default: http://milvus:19530)'
        )

        parser.add_argument(
            '-e', '--entity-limit',
            type=int,
            default=50,
            help=f'Entity vector fetch limit (default: 50)'
        )

        parser.add_argument(
            '-t', '--triple-limit',
            type=int,
            default=30,
            help=f'Triple query limit, per query (default: 30)'
        )

        parser.add_argument(
            '-u', '--max-subgraph-size',
            type=int,
            default=3000,
            help=f'Max subgraph size (default: 3000)'
        )

        parser.add_argument(
            '--prompt-request-queue',
            default=prompt_request_queue,
            help=f'Prompt request queue (default: {prompt_request_queue})',
        )

        parser.add_argument(
            '--prompt-response-queue',
            default=prompt_response_queue,
            help=f'Prompt response queue (default: {prompt_response_queue})',
        )

        parser.add_argument(
            '--embeddings-request-queue',
            default=embeddings_request_queue,
            help=f'Embeddings request queue (default: {embeddings_request_queue})',
        )

        parser.add_argument(
            '--embeddings-response-queue',
            default=embeddings_response_queue,
            help=f'Embeddings response queue (default: {embeddings_response_queue})',
        )

        parser.add_argument(
            '--document-embeddings-request-queue',
            default=document_embeddings_request_queue,
            help=f'Document embeddings request queue (default: {document_embeddings_request_queue})',
        )

        parser.add_argument(
            '--document-embeddings-response-queue',
            default=document_embeddings_response_queue,
            help=f'Document embeddings response queue (default: {document_embeddings_response_queue})',
        )

def run():

    Processor.start(module, __doc__)

