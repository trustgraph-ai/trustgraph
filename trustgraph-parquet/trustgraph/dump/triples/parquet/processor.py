
"""
Write graphs triples to parquet files in a directory.
"""

import pulsar
import base64
import os
import argparse
import time

from .... schema import Triple
from .... schema import triples_store_queue
from .... base import Consumer

from . writer import ParquetWriter

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = triples_store_queue
default_subscriber = module
default_graph_host='localhost'
default_directory = "."
default_file_template = "triples-{id}.parquet"
default_rotation_time = 60
        
class Processor(Consumer):

    def __init__(self, **params):
        
        input_queue = params.get("input_queue", default_input_queue)
        subscriber = params.get("subscriber", default_subscriber)
        directory = params.get("directory", default_directory)
        file_template = params.get("file_template", default_file_template)
        rotation_time = params.get("rotation_time", default_rotation_time)

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "subscriber": subscriber,
                "input_schema": Triple,
            }
        )

        self.writer = ParquetWriter(directory, file_template, rotation_time)

    def __del__(self):
        if hasattr(self, "writer"):
            del self.writer

    def handle(self, msg):

        v = msg.value()
        self.writer.write(v.s.value, v.p.value, v.o.value)

    @staticmethod
    def add_args(parser):

        Consumer.add_args(
            parser, default_input_queue, default_subscriber,
        )

        parser.add_argument(
            '-d', '--directory',
            default=default_directory,
            help=f'Directory to write to (default: {default_directory})'
        )

        parser.add_argument(
            '-f', '--file-template',
            default=default_file_template,
            help=f'Directory to write to (default: {default_file_template})'
        )

        parser.add_argument(
            '-t', '--rotation-time',
            type=int,
            default=default_rotation_time,
            help=f'Rotation time / seconds (default: {default_rotation_time})'
        )

def run():

    Processor.start(module, __doc__)

