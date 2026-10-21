
"""
Decision scoring service using Laya. Provides fast, structured
decision-making with three output types: choice, score, and noul.
Input is state + questions specification, output is answers with
confidence scores.
"""

import asyncio
import logging

from .... base import FlowProcessor, ConsumerSpec, ProducerSpec
from .... base import ParameterSpec
from .... schema import DecisionScoringRequest, DecisionScoringResponse
from .... schema import Error

logger = logging.getLogger(__name__)

default_ident = "decision-scoring"


class Processor(FlowProcessor):

    def __init__(self, **params):

        model = params.get("model")

        init_params = params
        if model:
            init_params = params | {"model": model}

        super(Processor, self).__init__(**init_params)

        self.model_override = model

        self.register_specification(
            ParameterSpec(name="model")
        )

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

        self.router = None

    async def start(self):

        from laya import Router

        logger.info("Loading Laya router with preloaded checkpoints...")
        loop = asyncio.get_event_loop()
        self.router = await loop.run_in_executor(
            None, lambda: Router(preload=True)
        )
        logger.info("Laya router loaded successfully")

        await super().start()

    async def on_request(self, msg, consumer, flow):

        request = msg.value()
        id = msg.properties()["id"]
        producer = flow("response")

        model = flow("model") or self.model_override

        if self.router is None:
            response = DecisionScoringResponse(
                error=Error(
                    type="not-ready",
                    message="Laya router is still loading",
                ),
            )
            await producer.send(response, properties={"id": id})
            return

        try:

            kwargs = {}
            if model:
                kwargs["model"] = model

            result = self.router.predict(
                request.state, request.questions, **kwargs
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
            '-m', '--model',
            default=None,
            help='Laya model override (default: auto-route by language)'
        )


def run():

    Processor.launch(default_ident, __doc__)
