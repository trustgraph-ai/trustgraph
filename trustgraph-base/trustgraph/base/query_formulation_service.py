"""
Query formulation service base class.  Input is a natural language
question and a schema name.  Output is a QuerySpecArtifact — a
structured query that a store-specific data service can execute.

Uses the prompt service for LLM calls and config events to load
data source schemas.
"""

from __future__ import annotations

from argparse import ArgumentParser

import time
import logging
from prometheus_client import Histogram

from .. schema import (
    QueryFormulationRequest, QueryFormulationResponse, Error,
)

from . flow_processor import FlowProcessor
from . consumer_spec import ConsumerSpec
from . producer_spec import ProducerSpec

logger = logging.getLogger(__name__)

default_ident = "query-formulation"
default_concurrency = 5


class QueryFormulationService(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")
        concurrency = params.get("concurrency", default_concurrency)

        super(QueryFormulationService, self).__init__(
            **params | {"id": id}
        )

        self.register_specification(
            ConsumerSpec(
                name="request",
                schema=QueryFormulationRequest,
                handler=self.on_message,
                concurrency=concurrency,
            )
        )

        self.register_specification(
            ProducerSpec(
                name="response",
                schema=QueryFormulationResponse,
            )
        )

        self.register_config_handler(
            self.on_schema_config,
            types=["schema"],
        )

        self.schemas = {}

        if not hasattr(__class__, "formulation_duration_metric"):
            from . metrics import BUCKETS_LLM
            __class__.formulation_duration_metric = Histogram(
                'tg_query_formulation_duration_seconds',
                'Query formulation request latency (seconds)',
                ["processor"],
                buckets=BUCKETS_LLM,
            )

    async def on_schema_config(self, workspace, config, version):

        logger.info(
            f"Loading schemas for workspace {workspace} "
            f"(version {version})"
        )

        schema_config = config.get("schema", {})

        schemas = {}
        for key, value in schema_config.items():
            try:
                import json
                schema = json.loads(value)
                schemas[key] = schema
                logger.info(f"Loaded schema '{key}'")
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(
                    f"Failed to load schema '{key}': {e}"
                )

        self.schemas[workspace] = schemas

        logger.info(
            f"Query formulation has {len(schemas)} schemas "
            f"for workspace {workspace}"
        )

    async def on_message(self, msg, consumer, flow):

        try:

            request = msg.value()
            id = msg.properties()["id"]

            logger.debug(f"Handling query formulation request {id}...")

            workspace = flow.workspace

            t0 = time.monotonic()
            response = await self.formulate(workspace, request, flow)
            __class__.formulation_duration_metric.labels(
                processor=self.id,
            ).observe(time.monotonic() - t0)

            logger.debug("Sending query formulation response...")
            await flow("response").send(response, properties={"id": id})
            logger.debug("Query formulation request completed")

        except Exception as e:

            logger.error(
                f"Exception in query formulation service: {e}",
                exc_info=True,
            )

            logger.info("Sending error response...")

            r = QueryFormulationResponse(
                error=Error(
                    type="query-formulation-error",
                    message=str(e),
                ),
            )

            await flow("response").send(r, properties={"id": id})

    def get_schema(self, workspace, schema_name):
        schemas = self.schemas.get(workspace, {})
        schema = schemas.get(schema_name)
        if schema is None:
            available = list(schemas.keys())
            raise ValueError(
                f"Schema '{schema_name}' not found. "
                f"Available: {available}"
            )
        return schema

    async def formulate(self, workspace, request, flow):
        raise NotImplementedError(
            "Subclasses must implement formulate"
        )

    @staticmethod
    def add_args(parser: ArgumentParser) -> None:
        FlowProcessor.add_args(parser)
