
"""
Decision scoring service using Laya via ONNX Runtime. Provides fast,
structured decision-making with three output types: choice, score, and
noul. Input is state + questions specification, output is answers with
confidence scores.
"""

import asyncio
import logging

from .... base import FlowProcessor, ConsumerSpec, ProducerSpec
from .... schema import DecisionScoringRequest, DecisionScoringResponse
from .... schema import Error

from . engine import OnnxEngine, DEFAULT_REPO

logger = logging.getLogger(__name__)

default_ident = "decision-scoring"


class Processor(FlowProcessor):

    def __init__(self, **params):

        super(Processor, self).__init__(**params)

        self.repo_id = params.get("model_repo") or DEFAULT_REPO
        self.variant = params.get("model_variant") or "fp32"

        self.register_specification(
            ConsumerSpec(
                name="request",
                schema=DecisionScoringRequest,
                handler=self.on_request,
            )
        )

        self.register_specification(
            ProducerSpec(
                name="response",
                schema=DecisionScoringResponse,
            )
        )

        self.engine = None

    async def start(self):

        logger.info("Loading Laya ONNX engine...")
        loop = asyncio.get_event_loop()
        self.engine = await loop.run_in_executor(
            None,
            lambda: OnnxEngine(
                repo_id=self.repo_id, variant=self.variant,
            ),
        )
        logger.info("Laya ONNX engine loaded successfully")

        await super().start()

    async def on_request(self, msg, consumer, flow):

        request = msg.value()
        id = msg.properties()["id"]
        producer = flow("response")

        if self.engine is None:
            response = DecisionScoringResponse(
                error=Error(
                    type="not-ready",
                    message="Laya ONNX engine is still loading",
                ),
            )
            await producer.send(response, properties={"id": id})
            return

        try:

            result = self.engine.predict(
                request.state, request.questions,
            )

            answers = result.get("answers", {})
            routing = result.get("routing", {})
            model_used = routing.get("model", "")

            response = DecisionScoringResponse(
                answers=answers,
                model=model_used,
            )

        except Exception as e:
            logger.error(f"Decision scoring error: {e}")
            response = DecisionScoringResponse(
                error=Error(
                    type="decision-scoring-error",
                    message=str(e),
                ),
            )

        await producer.send(response, properties={"id": id})

    @staticmethod
    def add_args(parser):

        FlowProcessor.add_args(parser)

        parser.add_argument(
            '--model-repo',
            default=None,
            help='HuggingFace repo for ONNX model (default: %s)'
            % DEFAULT_REPO,
        )

        parser.add_argument(
            '--model-variant',
            default="fp32",
            choices=["fp32", "fp16"],
            help='Model precision variant (default: fp32)',
        )


def run():

    Processor.launch(default_ident, __doc__)
