"""
Keyword index service base class.  A single service owns both sides of the
lexical index: it consumes Chunk messages off the ingestion stream (the last
message in the pipeline that still carries chunk text) and answers keyword
search requests over what it has indexed.  Unlike the vector stores, ingest
and query are not split into two processors: the first backend (SQLite FTS5)
is a single-file index that cannot be shared between containers, so one
process must own it.  Backends with a server (Elasticsearch/OpenSearch) can
still be split later behind the same schema.
"""

from __future__ import annotations

from argparse import ArgumentParser

import logging

from .. schema import Chunk
from .. schema import KeywordIndexRequest, KeywordIndexResponse
from .. schema import Error
from .. exceptions import TooManyRequests

from . flow_processor import FlowProcessor
from . consumer_spec import ConsumerSpec
from . producer_spec import ProducerSpec

# Module logger
logger = logging.getLogger(__name__)

default_ident = "kw-index"
default_concurrency = 10

class KeywordIndexService(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")
        concurrency = params.get("concurrency", default_concurrency)

        super(KeywordIndexService, self).__init__(
            **params | { "id": id }
        )

        self.register_specification(
            ConsumerSpec(
                name = "input",
                schema = Chunk,
                handler = self.on_chunk,
            )
        )

        self.register_specification(
            ConsumerSpec(
                name = "request",
                schema = KeywordIndexRequest,
                handler = self.on_request,
                concurrency = concurrency,
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "response",
                schema = KeywordIndexResponse,
            )
        )

    async def on_chunk(self, msg, consumer, flow):

        try:

            request = msg.value()

            # Workspace comes from the flow the message arrived on.
            await self.index_chunk(flow.workspace, request)

        except TooManyRequests as e:
            raise e

        except Exception as e:

            logger.error(f"Exception in keyword index store: {e}", exc_info=True)
            raise e

    async def on_request(self, msg, consumer, flow):

        try:

            request = msg.value()

            # Sender-produced ID
            id = msg.properties()["id"]

            logger.debug(f"Handling keyword index query request {id}...")

            chunks = await self.query_keyword_index(
                flow.workspace, request,
            )

            logger.debug("Sending keyword index query response...")
            r = KeywordIndexResponse(chunks=chunks, error=None)
            await flow("response").send(r, properties={"id": id})

            logger.debug("Keyword index query request completed")

        except Exception as e:

            logger.error(f"Exception in keyword index query service: {e}", exc_info=True)

            logger.info("Sending error response...")

            r = KeywordIndexResponse(
                error=Error(
                    type = "keyword-index-query-error",
                    message = str(e),
                ),
                chunks=[],
            )

            await flow("response").send(r, properties={"id": id})

    @staticmethod
    def add_args(parser: ArgumentParser) -> None:

        FlowProcessor.add_args(parser)

        parser.add_argument(
            '-c', '--concurrency',
            type=int,
            default=default_concurrency,
            help=f'Number of concurrent requests (default: {default_concurrency})'
        )
