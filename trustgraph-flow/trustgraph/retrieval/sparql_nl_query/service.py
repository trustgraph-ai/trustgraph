"""
SPARQL NL Query orchestration service. Takes a natural language question,
chains through NL-to-SPARQL translation and SPARQL execution, returning
both the generated query and its results.
"""

import logging

from ... schema import (
    SparqlNLQueryRequest, SparqlNLQueryResponse,
    QuestionToSparqlRequest, QuestionToSparqlResponse,
    SparqlQueryRequest, SparqlQueryResponse,
    Error, IRI, LITERAL, TRIPLE,
)
from ... base import FlowProcessor, ConsumerSpec, ProducerSpec
from ... base import RequestResponseSpec

logger = logging.getLogger(__name__)

default_ident = "sparql-nl-query"


class Processor(FlowProcessor):

    def __init__(self, **params):
        id = params.get("id", default_ident)

        super(Processor, self).__init__(
            **params | {
                "id": id,
            }
        )

        self.register_specification(
            ConsumerSpec(
                name="request",
                schema=SparqlNLQueryRequest,
                handler=self.on_message,
            )
        )

        self.register_specification(
            ProducerSpec(
                name="response",
                schema=SparqlNLQueryResponse,
            )
        )

        self.register_specification(
            RequestResponseSpec(
                request_name="nl-sparql-request",
                response_name="nl-sparql-response",
                request_schema=QuestionToSparqlRequest,
                response_schema=QuestionToSparqlResponse,
            )
        )

        self.register_specification(
            RequestResponseSpec(
                request_name="sparql-request",
                response_name="sparql-response",
                request_schema=SparqlQueryRequest,
                response_schema=SparqlQueryResponse,
            )
        )

    async def on_message(self, msg, consumer, flow):
        try:
            request = msg.value()
            id = msg.properties()["id"]

            response = await self._execute(flow, request)

            await flow("response").send(
                response, properties={"id": id}
            )

        except Exception as e:
            logger.error(
                f"SPARQL NL query service error: {e}", exc_info=True
            )

            await flow("response").send(
                SparqlNLQueryResponse(
                    error=Error(
                        type="sparql-nl-query-error",
                        message=str(e),
                    ),
                ),
                properties={"id": id},
            )

    async def _execute(self, flow, request):
        question = request.question
        collection = request.collection or "default"
        limit = request.limit or 10

        logger.info(
            f"Translating question to SPARQL: {question[:100]}..."
        )

        nl_response = await flow("nl-sparql-request").request(
            QuestionToSparqlRequest(
                question=question,
                collection=collection,
                limit=limit,
            )
        )

        if nl_response.error is not None:
            return SparqlNLQueryResponse(
                error=Error(
                    type="nl-sparql-error",
                    message=nl_response.error.message,
                ),
            )

        if not nl_response.sparql:
            return SparqlNLQueryResponse(
                error=Error(
                    type="nl-sparql-error",
                    message="NL-to-SPARQL returned empty query",
                ),
            )

        logger.info(
            f"Generated SPARQL ({len(nl_response.sparql)} chars), "
            f"executing..."
        )

        sparql_response = await flow("sparql-request").request(
            SparqlQueryRequest(
                query=nl_response.sparql,
                collection=collection,
                limit=limit,
            )
        )

        if sparql_response.error is not None:
            return SparqlNLQueryResponse(
                sparql=nl_response.sparql,
                resolved_entities=nl_response.resolved_entities,
                error=Error(
                    type="sparql-execution-error",
                    message=sparql_response.error.message,
                ),
            )

        bindings_as_strings = []
        for binding in sparql_response.bindings:
            row = []
            for term in binding.values:
                row.append(self._term_to_string(term))
            bindings_as_strings.append(row)

        logger.info(
            f"SPARQL returned {len(bindings_as_strings)} rows"
        )

        return SparqlNLQueryResponse(
            sparql=nl_response.sparql,
            resolved_entities=nl_response.resolved_entities,
            query_type=sparql_response.query_type,
            variables=sparql_response.variables,
            bindings=bindings_as_strings,
            ask_result=sparql_response.ask_result,
        )

    @staticmethod
    def _term_to_string(term):
        if term is None:
            return ""
        if term.type == IRI:
            return term.iri
        if term.type == LITERAL:
            return term.value
        if term.type == TRIPLE:
            return str(term)
        return str(term)

    @staticmethod
    def add_args(parser):
        FlowProcessor.add_args(parser)


def run():
    Processor.launch(default_ident, __doc__)
