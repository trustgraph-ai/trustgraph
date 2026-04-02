"""
SPARQL query service. Accepts SPARQL queries, decomposes them into triple
pattern lookups via the triples query pub/sub interface, performs in-memory
joins/filters/projections, and returns SPARQL result bindings.
"""

import logging

from ... schema import SparqlQueryRequest, SparqlQueryResponse
from ... schema import SparqlBinding, Error, Term, Triple
from ... base import FlowProcessor, ConsumerSpec, ProducerSpec
from ... base import TriplesClientSpec

from . parser import parse_sparql, ParseError
from . algebra import evaluate, EvaluationError

logger = logging.getLogger(__name__)

default_ident = "sparql-query"
default_concurrency = 10


class Processor(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id", default_ident)
        concurrency = params.get("concurrency", default_concurrency)

        super(Processor, self).__init__(
            **params | {
                "id": id,
                "concurrency": concurrency,
            }
        )

        self.register_specification(
            ConsumerSpec(
                name="request",
                schema=SparqlQueryRequest,
                handler=self.on_message,
                concurrency=concurrency,
            )
        )

        self.register_specification(
            ProducerSpec(
                name="response",
                schema=SparqlQueryResponse,
            )
        )

        self.register_specification(
            TriplesClientSpec(
                request_name="triples-request",
                response_name="triples-response",
            )
        )

    async def on_message(self, msg, consumer, flow):

        try:

            request = msg.value()
            id = msg.properties()["id"]

            logger.debug(f"Handling SPARQL query request {id}...")

            response = await self.execute_sparql(request, flow)

            await flow("response").send(response, properties={"id": id})

            logger.debug("SPARQL query request completed")

        except Exception as e:

            logger.error(
                f"Exception in SPARQL query service: {e}", exc_info=True
            )

            r = SparqlQueryResponse(
                error=Error(
                    type="sparql-query-error",
                    message=str(e),
                ),
            )

            await flow("response").send(r, properties={"id": id})

    async def execute_sparql(self, request, flow):
        """Parse and evaluate a SPARQL query."""

        # Parse the SPARQL query
        try:
            parsed = parse_sparql(request.query)
        except ParseError as e:
            return SparqlQueryResponse(
                error=Error(
                    type="sparql-parse-error",
                    message=str(e),
                ),
            )

        # Get the triples client from the flow
        triples_client = flow("triples-request")

        # Evaluate the algebra
        try:
            solutions = await evaluate(
                parsed.algebra,
                triples_client,
                user=request.user or "trustgraph",
                collection=request.collection or "default",
                limit=request.limit or 10000,
            )
        except EvaluationError as e:
            return SparqlQueryResponse(
                error=Error(
                    type="sparql-evaluation-error",
                    message=str(e),
                ),
            )

        # Build response based on query type
        if parsed.query_type == "select":
            return self._build_select_response(parsed, solutions)
        elif parsed.query_type == "ask":
            return self._build_ask_response(solutions)
        elif parsed.query_type == "construct":
            return self._build_construct_response(parsed, solutions)
        elif parsed.query_type == "describe":
            return self._build_describe_response(parsed, solutions)
        else:
            return SparqlQueryResponse(
                error=Error(
                    type="sparql-unsupported",
                    message=f"Unsupported query type: {parsed.query_type}",
                ),
            )

    def _build_select_response(self, parsed, solutions):
        """Build response for SELECT queries."""
        variables = parsed.variables

        bindings = []
        for sol in solutions:
            values = [sol.get(v) for v in variables]
            bindings.append(SparqlBinding(values=values))

        return SparqlQueryResponse(
            query_type="select",
            variables=variables,
            bindings=bindings,
        )

    def _build_ask_response(self, solutions):
        """Build response for ASK queries."""
        return SparqlQueryResponse(
            query_type="ask",
            ask_result=len(solutions) > 0,
        )

    def _build_construct_response(self, parsed, solutions):
        """Build response for CONSTRUCT queries."""
        # CONSTRUCT template is in the algebra
        template = []
        if hasattr(parsed.algebra, "template"):
            template = parsed.algebra.template

        triples = []
        seen = set()

        for sol in solutions:
            for s_tmpl, p_tmpl, o_tmpl in template:
                from rdflib.term import Variable
                from . parser import rdflib_term_to_term

                s = self._resolve_construct_term(s_tmpl, sol)
                p = self._resolve_construct_term(p_tmpl, sol)
                o = self._resolve_construct_term(o_tmpl, sol)

                if s is not None and p is not None and o is not None:
                    key = (
                        s.type, s.iri or s.value,
                        p.type, p.iri or p.value,
                        o.type, o.iri or o.value,
                    )
                    if key not in seen:
                        seen.add(key)
                        triples.append(Triple(s=s, p=p, o=o))

        return SparqlQueryResponse(
            query_type="construct",
            triples=triples,
        )

    def _build_describe_response(self, parsed, solutions):
        """Build response for DESCRIBE queries."""
        # DESCRIBE returns all triples about the described resources
        # For now, return empty - would need additional triples queries
        return SparqlQueryResponse(
            query_type="describe",
            triples=[],
        )

    def _resolve_construct_term(self, tmpl, solution):
        """Resolve a CONSTRUCT template term."""
        from rdflib.term import Variable
        from . parser import rdflib_term_to_term

        if isinstance(tmpl, Variable):
            return solution.get(str(tmpl))
        else:
            return rdflib_term_to_term(tmpl)

    @staticmethod
    def add_args(parser):
        FlowProcessor.add_args(parser)

        parser.add_argument(
            '-c', '--concurrency',
            type=int,
            default=default_concurrency,
            help=f'Number of concurrent requests '
                 f'(default: {default_concurrency})'
        )


def run():
    Processor.launch(default_ident, __doc__)
