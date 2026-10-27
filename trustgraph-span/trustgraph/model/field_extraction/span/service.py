
"""
Field extraction service using BIO span extraction via ONNX Runtime.
Extracts verbatim text spans from input based on field instructions.
"""

import asyncio
import logging

from .... base import FlowProcessor, ConsumerSpec, ProducerSpec, ParameterSpec
from .... schema import FieldExtractionRequest, FieldExtractionResponse
from .... schema import Error

from . engine import OnnxEngine, DEFAULT_REPO, DEFAULT_MAX_LENGTH

logger = logging.getLogger(__name__)

default_ident = "field-extraction"


class Processor(FlowProcessor):

    def __init__(self, **params):

        super(Processor, self).__init__(**params)

        self.repo_id = params.get("model") or DEFAULT_REPO
        self.max_length = int(
            params.get("max-length") or DEFAULT_MAX_LENGTH
        )

        self.register_specification(
            ParameterSpec(
                name="model",
            )
        )

        self.register_specification(
            ParameterSpec(
                name="max-length",
            )
        )

        self.register_specification(
            ConsumerSpec(
                name="request",
                schema=FieldExtractionRequest,
                handler=self.on_request,
            )
        )

        self.register_specification(
            ProducerSpec(
                name="response",
                schema=FieldExtractionResponse,
            )
        )

        self.engine = None

    async def start(self):

        logger.info("Loading span-extraction ONNX engine...")
        loop = asyncio.get_event_loop()
        self.engine = await loop.run_in_executor(
            None,
            lambda: OnnxEngine(
                repo_id=self.repo_id, max_length=self.max_length,
            ),
        )
        logger.info("Span-extraction ONNX engine loaded successfully")

        await super().start()

    async def on_request(self, msg, consumer, flow):

        request = msg.value()
        id = msg.properties()["id"]
        producer = flow("response")

        if self.engine is None:
            response = FieldExtractionResponse(
                error=Error(
                    type="not-ready",
                    message="Span-extraction engine is still loading",
                ),
            )
            await producer.send(response, properties={"id": id})
            return

        try:

            result = self.engine.predict(
                request.state, request.fields,
            )

            response = FieldExtractionResponse(
                answers=result.get("answers", {}),
                model=result.get("model", ""),
            )

        except Exception as e:
            logger.error(f"Field extraction error: {e}")
            response = FieldExtractionResponse(
                error=Error(
                    type="field-extraction-error",
                    message=str(e),
                ),
            )

        await producer.send(response, properties={"id": id})

    @staticmethod
    def add_args(parser):

        FlowProcessor.add_args(parser)

        parser.add_argument(
            '--model',
            default=None,
            help='HuggingFace repo for ONNX model (default: %s)'
            % DEFAULT_REPO,
        )

        parser.add_argument(
            '--max-length',
            default=None,
            type=int,
            help='Max token sequence length (default: %d)'
            % DEFAULT_MAX_LENGTH,
        )


def run():

    Processor.launch(default_ident, __doc__)
