"""
Base chunking service that provides parameter specification functionality
for chunk-size and chunk-overlap parameters, and librarian client for
fetching large document content.
"""

import asyncio
import base64
import logging

from .flow_processor import FlowProcessor
from .parameter_spec import ParameterSpec
from .librarian_client import LibrarianClient

# Module logger
logger = logging.getLogger(__name__)


class ChunkingService(FlowProcessor):
    """Base service for chunking processors with parameter specification support"""

    def __init__(self, **params):

        id = params.get("id", "chunker")

        # Call parent constructor
        super(ChunkingService, self).__init__(**params)

        # Register parameter specifications for chunk-size and chunk-overlap
        self.register_specification(
            ParameterSpec(name="chunk-size")
        )

        self.register_specification(
            ParameterSpec(name="chunk-overlap")
        )

        # Librarian client
        self.librarian = LibrarianClient(
            id=id,
            backend=self.pubsub,
            taskgroup=self.taskgroup,
        )

        logger.debug("ChunkingService initialized with parameter specifications")

    async def start(self):
        await super(ChunkingService, self).start()
        await self.librarian.start()

    async def get_document_text(self, doc, workspace):
        """
        Get text content from a TextDocument, fetching from librarian if needed.

        Args:
            doc: TextDocument with either inline text or document_id
            workspace: Workspace for librarian lookup (from flow.workspace)

        Returns:
            str: The document text content
        """
        if doc.document_id and not doc.text:
            logger.info(f"Fetching document {doc.document_id} from librarian...")
            text = await self.librarian.fetch_document_text(
                document_id=doc.document_id,
                workspace=workspace,
            )
            logger.info(f"Fetched {len(text)} characters from librarian")
            return text
        else:
            return doc.text.decode("utf-8")

    async def chunk_document(self, msg, consumer, flow, default_chunk_size, default_chunk_overlap):
        """
        Extract chunk parameters from flow and return effective values

        Args:
            msg: The message being processed
            consumer: The consumer instance
            flow: The flow object containing parameters
            default_chunk_size: Default chunk size if not configured
            default_chunk_overlap: Default chunk overlap if not configured

        Returns:
            tuple: (chunk_size, chunk_overlap) effective values
        """

        chunk_size = default_chunk_size
        chunk_overlap = default_chunk_overlap

        try:
            cs = flow("chunk-size")
            if cs is not None:
                chunk_size = int(cs)
        except Exception as e:
            logger.warning(f"Could not parse chunk-size parameter: {e}")

        try:
            co = flow("chunk-overlap")
            if co is not None:
                chunk_overlap = int(co)
        except Exception as e:
            logger.warning(f"Could not parse chunk-overlap parameter: {e}")

        return chunk_size, chunk_overlap
