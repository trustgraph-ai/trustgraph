"""
Concept extraction service.  Extracts key concepts from a
natural-language query using an LLM prompt.  The extracted concepts
are suitable for downstream embedding and entity retrieval.
"""

import logging

from ... schema import (
    ConceptExtractionRequest, ConceptExtractionResponse,
)
from ... base import ConceptExtractionService, PromptClientSpec

logger = logging.getLogger(__name__)

default_ident = "concept-extraction"


class Processor(ConceptExtractionService):

    def __init__(self, **params):

        super(Processor, self).__init__(**params)

        self.register_specification(
            PromptClientSpec(
                request_name="prompt-request",
                response_name="prompt-response",
            )
        )

    async def extract(self, workspace, request, flow):

        query = request.query
        if not query:
            return ConceptExtractionResponse(concepts=[])

        logger.info(f"Extracting concepts from: {query[:80]}...")

        prompt_client = flow("prompt-request")

        result = await prompt_client.prompt(
            "extract-concepts",
            variables={"query": query},
        )

        concepts = []
        if result.text:
            for line in result.text.strip().split('\n'):
                line = line.strip()
                if line:
                    concepts.append(line)

        if not concepts:
            concepts = [query]

        logger.info(f"Extracted {len(concepts)} concepts")

        return ConceptExtractionResponse(concepts=concepts)

    @staticmethod
    def add_args(parser):
        ConceptExtractionService.add_args(parser)


def run():
    Processor.launch(default_ident, __doc__)
