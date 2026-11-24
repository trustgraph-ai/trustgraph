"""
Base class for remote action services.

Remote action services are standalone services that implement
execution capabilities outside a flow.  They receive typed ActionRequests
and return typed artifacts.

Uses direct topics (no flow configuration required).
"""

from __future__ import annotations

from argparse import ArgumentParser

import json
import logging
from prometheus_client import Counter

from .. schema import RemoteActionRequest, RemoteActionResponse, Error
from .. schema import UserContext
from .. schema.core.topic import queue
from .. base.serialization import dict_to_dataclass, dataclass_to_dict
from .. exceptions import TooManyRequests
from . async_processor import AsyncProcessor

logger = logging.getLogger(__name__)

default_topic = "action"


class RemoteActionService(AsyncProcessor):

    def __init__(self, **params):

        super(RemoteActionService, self).__init__(**params)

        self.id = params.get("id")
        self._topic = params.get("topic", default_topic)

        self._consumer_reg = None
        self._producer_handle = None

        if not hasattr(__class__, "remote_action_metric"):
            __class__.remote_action_metric = Counter(
                'tg_remote_action_invocation_total',
                'Remote action service invocation count',
                ["processor"],
            )

    async def start(self):
        await super(RemoteActionService, self).start()

        request_topic = queue(self._topic, cls='request')
        response_topic = queue(self._topic, cls='response')

        logger.info(
            f"Remote action service topics: "
            f"request={request_topic}, response={response_topic}"
        )

        self._producer_handle = await self.sender_pool.add_producer(
            topic=response_topic,
            schema=RemoteActionResponse,
        )

        async def handler(message):
            await self.on_request(message)

        self._consumer_reg = await self.receiver_pool.add_consumer(
            topic=request_topic,
            subscription=f"{self.id}-request",
            schema=RemoteActionRequest,
            handler=handler,
        )

        logger.info(f"Remote action service {self.id} started")

    async def on_request(self, msg):

        id = None

        try:

            request = msg.value()

            id = msg.properties().get("id", "unknown")

            params = (
                json.loads(request.params) if request.params else {}
            )

            inputs = {}
            for key, value in params.items():
                if isinstance(value, dict) and "artifact" in value:
                    inputs[key] = value["artifact"]
                else:
                    inputs[key] = value

            user_context = None
            if request.user_context:
                uc_dict = json.loads(request.user_context)
                user_context = dict_to_dataclass(uc_dict, UserContext)

            logger.info(
                f"Executing {request.capability} for "
                f"run {request.run_id} step {request.step_id}"
            )

            result = await self.execute(inputs, user_context)

            artifacts = {}
            for name, (artifact_type, artifact) in result.items():
                artifacts[name] = {
                    "artifact-type": artifact_type,
                    "artifact": artifact,
                }

            await self._producer_handle.send(
                RemoteActionResponse(
                    run_id=request.run_id,
                    step_id=request.step_id,
                    artifacts=json.dumps(artifacts),
                ),
                properties={"id": id}
            )

            __class__.remote_action_metric.labels(
                processor=self.id,
            ).inc()

        except TooManyRequests as e:
            raise e

        except Exception as e:

            logger.error(
                f"Exception in remote action service: {e}",
                exc_info=True,
            )

            await self._producer_handle.send(
                RemoteActionResponse(
                    run_id=request.run_id if request else "",
                    step_id=request.step_id if request else "",
                    error=Error(
                        type="remote-action-error",
                        message=str(e),
                    ),
                ),
                properties={"id": id if id else "unknown"}
            )

    async def execute(self, inputs, user_context):
        raise NotImplementedError("Subclasses must implement execute()")

    @staticmethod
    def add_args(parser: ArgumentParser) -> None:

        AsyncProcessor.add_args(parser)

        parser.add_argument(
            '-t', '--topic',
            default=default_topic,
            help=f'Topic name for request/response '
                 f'(default: {default_topic})'
        )
