
"""
Graph embeddings, calls the embeddings service to get embeddings for a
set of entity contexts.  Input is entity plus textual context.
Output is entity plus embedding.
"""

from ... schema import EntityContexts, EntityEmbeddings, GraphEmbeddings
from ... schema import entity_contexts_ingest_queue
from ... schema import graph_embeddings_store_queue
from ... schema import embeddings_request_queue, embeddings_response_queue
from ... clients.embeddings_client import EmbeddingsClient
from ... log_level import LogLevel
from ... base import FlowProcessor

module = "graph-embeddings"

default_subscriber = module

class Processor(FlowProcessor):

    def __init__(self, **params):



                "input_schema": EntityContexts,
                "output_schema": GraphEmbeddings,
        



        id = params.get("id")
        subscriber = params.get("subscriber", default_subscriber)

        super(Processor, self).__init__(
            **params | {
                "id": id,
                "subscriber": subscriber,
            }
        )

        self.register_consumer(
            name = "input",
            schema = EntityContexts,
            handler = self.on_message,
        )

        self.register_producer(
            name = "output",
            schema = GraphEmbeddings,
        )

        # self.embeddings = EmbeddingsClient(
        #     pulsar_host=self.pulsar_host,
        #     input_queue=emb_request_queue,
        #     output_queue=emb_response_queue,
        #     subscriber=module + "-emb",
        # )

    async def handle(self, msg):

        v = msg.value()
        print(f"Indexing {v.metadata.id}...", flush=True)

        entities = []

        try:

            for entity in v.entities:

                vectors = self.embeddings.request(entity.context)

                entities.append(
                    EntityEmbeddings(
                        entity=entity.entity,
                        vectors=vectors
                    )
                )

            r = GraphEmbeddings(
                metadata=v.metadata,
                entities=entities,
            )

            await self.send(r)

        except Exception as e:
            print("Exception:", e, flush=True)

            # Retry
            raise e

        print("Done.", flush=True)

    @staticmethod
    def add_args(parser):

        ConsumerProducer.add_args(
            parser, default_input_queue, default_subscriber,
            default_output_queue,
        )

        parser.add_argument(
            '--embeddings-request-queue',
            default=embeddings_request_queue,
            help=f'Embeddings request queue (default: {embeddings_request_queue})',
        )

        parser.add_argument(
            '--embeddings-response-queue',
            default=embeddings_response_queue,
            help=f'Embeddings request queue (default: {embeddings_response_queue})',
        )

def run():

    Processor.launch(module, __doc__)

