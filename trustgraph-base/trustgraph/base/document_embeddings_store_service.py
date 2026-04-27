"""
Document embeddings store base class
"""

from __future__ import annotations

from argparse import ArgumentParser

import logging

from .. schema import DocumentEmbeddings
from .. base import FlowProcessor, ConsumerSpec
from .. exceptions import TooManyRequests

# Module logger
logger = logging.getLogger(__name__)

default_ident = "document-embeddings-write"

class DocumentEmbeddingsStoreService(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")

        super(DocumentEmbeddingsStoreService, self).__init__(
            **params | { "id": id }
        )

        self.register_specification(
            ConsumerSpec(
                name = "input",
                schema = DocumentEmbeddings,
                handler = self.on_message
            )
        )

    async def on_message(self, msg, consumer, flow):

        try:

            request = msg.value()

            # Workspace comes from the flow the message arrived on.
            await self.store_document_embeddings(flow.workspace, request)

        except TooManyRequests as e:
            raise e

        except Exception as e:
            
            logger.error(f"Exception in document embeddings store service: {e}", exc_info=True)
            raise e

    @staticmethod
    def add_args(parser: ArgumentParser) -> None:

        FlowProcessor.add_args(parser)

