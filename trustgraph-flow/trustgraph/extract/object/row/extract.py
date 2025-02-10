
"""
Simple decoder, accepts vector+text chunks input, applies analysis to pull
out a row of fields.  Output as a vector plus object.
"""

import urllib.parse
import os
from pulsar.schema import JsonSchema

from .... schema import ChunkEmbeddings, Rows, ObjectEmbeddings, Metadata
from .... schema import RowSchema, Field
from .... schema import chunk_embeddings_ingest_queue, rows_store_queue
from .... schema import object_embeddings_store_queue
from .... schema import prompt_request_queue
from .... schema import prompt_response_queue
from .... log_level import LogLevel
from .... clients.prompt_client import PromptClient
from .... base import ConsumerProducer

from .... objects.field import Field as FieldParser
from .... objects.object import Schema

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = chunk_embeddings_ingest_queue
default_output_queue = rows_store_queue
default_vector_queue = object_embeddings_store_queue
default_subscriber = module

class Processor(ConsumerProducer):

    def __init__(self, **params):

        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        vector_queue = params.get("vector_queue", default_vector_queue)
        subscriber = params.get("subscriber", default_subscriber)
        pr_request_queue = params.get(
            "prompt_request_queue", prompt_request_queue
        )
        pr_response_queue = params.get(
            "prompt_response_queue", prompt_response_queue
        )

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "output_queue": output_queue,
                "subscriber": subscriber,
                "input_schema": ChunkEmbeddings,
                "output_schema": Rows,
                "prompt_request_queue": pr_request_queue,
                "prompt_response_queue": pr_response_queue,
            }
        )

        self.vec_prod = self.client.create_producer(
            topic=vector_queue,
            schema=JsonSchema(ObjectEmbeddings),
        )

        __class__.pubsub_metric.info({
            "input_queue": input_queue,
            "output_queue": output_queue,
            "vector_queue": vector_queue,
            "prompt_request_queue": pr_request_queue,
            "prompt_response_queue": pr_response_queue,
            "subscriber": subscriber,
            "input_schema": ChunkEmbeddings.__name__,
            "output_schema": Rows.__name__,
            "vector_schema": ObjectEmbeddings.__name__,
        })

        flds = __class__.parse_fields(params["field"])

        for fld in flds:
            print(fld)

        self.primary = None

        for f in flds:
            if f.primary:
                if self.primary:
                    raise RuntimeError(
                        "Only one primary key field is supported"
                    )
                self.primary = f

        if self.primary == None:
            raise RuntimeError(
                "Must have exactly one primary key field"
            )

        self.schema = Schema(
            name = params["name"],
            description = params["description"],
            fields = flds
        )

        self.row_schema=RowSchema(
            name=self.schema.name,
            description=self.schema.description,
            fields=[
                Field(
                     name=f.name, type=str(f.type), size=f.size,
                     primary=f.primary, description=f.description,
                )
                for f in self.schema.fields
            ]
        )

        self.prompt = PromptClient(
            pulsar_host=self.pulsar_host,
            pulsar_api_key=self.pulsar_api_key,
            input_queue=pr_request_queue,
            output_queue=pr_response_queue,
            subscriber = module + "-prompt",
        )

    @staticmethod
    def parse_fields(fields):
        return [ FieldParser.parse(f) for f in fields ]

    def get_rows(self, chunk):
        return self.prompt.request_rows(self.schema, chunk)

    def emit_rows(self, metadata, rows):

        t = Rows(
            metadata=metadata, row_schema=self.row_schema, rows=rows
        )
        self.producer.send(t)

    def emit_vec(self, metadata, name, vec, key_name, key):

        r = ObjectEmbeddings(
            metadata=metadata, vectors=vec, name=name, key_name=key_name, id=key
        )
        self.vec_prod.send(r)

    def handle(self, msg):

        v = msg.value()
        print(f"Indexing {v.metadata.id}...", flush=True)

        chunk = v.chunk.decode("utf-8")

        try:

            rows = self.get_rows(chunk)

            self.emit_rows(
                metadata=v.metadata,
                rows=rows
            )

            for row in rows:
                self.emit_vec(
                    metadata=v.metadata, vec=v.vectors,
                    name=self.schema.name, key_name=self.primary.name,
                    key=row[self.primary.name]
                )

            for row in rows:
                print(row)

        except Exception as e:
            print("Exception: ", e, flush=True)

        print("Done.", flush=True)

    @staticmethod
    def add_args(parser):

        ConsumerProducer.add_args(
            parser, default_input_queue, default_subscriber,
            default_output_queue,
        )

        parser.add_argument(
            '-c', '--vector-queue',
            default=default_vector_queue,
            help=f'Vector output queue (default: {default_vector_queue})'
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
            '-f', '--field',
            required=True,
            action='append',
            help=f'Field definition, format name:type:size:pri:descriptionn',
        )

        parser.add_argument(
            '-n', '--name',
            required=True,
            help=f'Name of row object',
        )

        parser.add_argument(
            '-d', '--description',
            required=True,
            help=f'Description of object',
        )

def run():

    Processor.start(module, __doc__)

