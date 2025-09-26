"""
Base chunking service that provides parameter specification functionality
for chunk-size and chunk-overlap parameters
"""

import logging
from .flow_processor import FlowProcessor
from .parameter_spec import ParameterSpec

# Module logger
logger = logging.getLogger(__name__)

class ChunkingService(FlowProcessor):
    """Base service for chunking processors with parameter specification support"""

    def __init__(self, **params):

        # Call parent constructor
        super(ChunkingService, self).__init__(**params)

        # Register parameter specifications for chunk-size and chunk-overlap
        self.register_specification(
            ParameterSpec(name="chunk-size")
        )

        self.register_specification(
            ParameterSpec(name="chunk-overlap")
        )

        logger.debug("ChunkingService initialized with parameter specifications")

    async def chunk_document(self, msg, consumer, flow, default_chunk_size, default_chunk_overlap):
        """
        Extract chunk parameters from flow and return effective values

        Args:
            msg: The message containing the document to chunk
            consumer: The consumer spec
            flow: The flow context
            default_chunk_size: Default chunk size from processor config
            default_chunk_overlap: Default chunk overlap from processor config

        Returns:
            tuple: (chunk_size, chunk_overlap) - effective values to use
        """
        # Extract parameters from flow (flow-configurable parameters)
        chunk_size = flow("chunk-size")
        chunk_overlap = flow("chunk-overlap")

        # Use provided values or fall back to defaults
        effective_chunk_size = chunk_size if chunk_size is not None else default_chunk_size
        effective_chunk_overlap = chunk_overlap if chunk_overlap is not None else default_chunk_overlap

        logger.debug(f"Using chunk-size: {effective_chunk_size}")
        logger.debug(f"Using chunk-overlap: {effective_chunk_overlap}")

        return effective_chunk_size, effective_chunk_overlap

    @staticmethod
    def add_args(parser):
        """Add chunking service arguments to parser"""
        FlowProcessor.add_args(parser)