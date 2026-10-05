
"""
Policy-filtered triples query service.

Same input interface as triples-query, but applies SHACL-AF policy
filtering to the response. Delegates the actual graph query to the
backing triples-query service via RPC.

Flow config selects between triples-query (no policy) and this
service.
"""

import logging
from uuid import uuid4

from ... schema import (
    TriplesQueryRequest, TriplesQueryResponse,
    Term, Triple, IRI, LITERAL, Error,
)
from ... base import (
    FlowProcessor, ConsumerSpec, ProducerSpec,
    TriplesClientSpec, PolicyEventPublisher,
)
from .. policy_filter import PolicyFilter, QueryCache, SparqlCache

logger = logging.getLogger(__name__)

default_ident = "triples-policy"
default_concurrency = 10


class Processor(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id", default_ident)
        concurrency = params.get("concurrency", default_concurrency)

        super(Processor, self).__init__(
            **params | {"id": id}
        )

        self._query_caches = {}
        self._sparql_cache = SparqlCache()
        self._policy_cache = {}

        self.register_specification(
            ConsumerSpec(
                name="request",
                schema=TriplesQueryRequest,
                handler=self.on_message,
                concurrency=concurrency,
            )
        )

        self.register_specification(
            TriplesClientSpec(
                request_name="triples-request",
                response_name="triples-response",
            )
        )

        self.register_specification(
            ProducerSpec(
                name="response",
                schema=TriplesQueryResponse,
            )
        )

        self.policy_event_publisher = PolicyEventPublisher(
            component_name=id,
        )

    async def start(self):
        await super().start()
        await self.policy_event_publisher.start(
            sender_pool=self.sender_pool,
        )

    async def stop(self):
        await self.policy_event_publisher.stop()
        await super().stop()

    async def on_message(self, msg, consumer, flow):

        try:

            request = msg.value()
            id = msg.properties()["id"]
            workspace = flow.workspace

            logger.debug(
                f"Handling policy-filtered triples query {id}..."
            )

            triples_client = flow("triples-request")

            resp = await triples_client.request(
                TriplesQueryRequest(
                    s=request.s,
                    p=request.p,
                    o=request.o,
                    limit=request.limit,
                    collection=request.collection,
                    g=request.g,
                ),
            )

            if resp.error:
                await flow("response").send(
                    TriplesQueryResponse(
                        error=resp.error,
                        triples=None,
                    ),
                    properties={"id": id},
                )
                return

            triples = resp.triples or []

            triples = await self._apply_policy(
                triples, request, workspace, triples_client,
            )

            if triples is None:
                await flow("response").send(
                    TriplesQueryResponse(
                        error=Error(
                            type="policy-enforcement-error",
                            message=(
                                "Policies are active but no "
                                "user_context was provided."
                            ),
                        ),
                        triples=None,
                    ),
                    properties={"id": id},
                )
                return

            r = TriplesQueryResponse(triples=triples, error=None)
            await flow("response").send(r, properties={"id": id})

            logger.debug(
                "Policy-filtered triples query completed"
            )

        except Exception as e:

            logger.error(
                f"Exception in policy triples query: {e}",
                exc_info=True,
            )

            r = TriplesQueryResponse(
                error=Error(
                    type="triples-query-policy-error",
                    message=str(e),
                ),
                triples=None,
            )

            await flow("response").send(r, properties={"id": id})

    async def _apply_policy(self, triples, request, workspace,
                            triples_client):
        """Apply policy filtering. Returns filtered triples, or None
        if enforcement mode rejects the request (policies exist but
        no user_context).
        """

        evaluations = []

        async def on_evaluation(ev):
            evaluations.append(ev)

        async def query_fn(s, p, o, collection, g=""):
            resp = await triples_client.request(
                TriplesQueryRequest(
                    s=s, p=p, o=o,
                    collection=collection, g=g,
                    limit=10000,
                ),
            )
            if resp.error:
                raise RuntimeError(resp.error.message)
            return resp.triples or []

        if workspace not in self._query_caches:
            self._query_caches[workspace] = QueryCache(query_fn)
        query_cache = self._query_caches[workspace]

        collection = request.collection or "default"
        policy_key = (workspace, collection)
        cached = self._policy_cache.get(policy_key)
        policies = cached[0] if cached else None
        required_predicates = cached[1] if cached else None

        policy_filter = PolicyFilter(
            query_fn=query_fn,
            on_evaluation=on_evaluation,
            query_cache=query_cache,
            sparql_cache=self._sparql_cache,
            policies=policies,
            required_predicates=required_predicates,
        )

        await policy_filter.load_policies(collection)

        if policy_key not in self._policy_cache and policy_filter._policies:
            self._policy_cache[policy_key] = (
                policy_filter._policies,
                policy_filter._required_predicates,
            )

        if policy_filter.has_policies() and not request.user_context:
            return None

        if not request.user_context:
            return triples

        filtered = await policy_filter.apply(
            triples, request.collection, request.user_context,
        )

        if evaluations:
            await self.policy_event_publisher.emit_evaluations(
                evaluations=evaluations,
                user_context=request.user_context,
                request_id=str(uuid4()),
                query_s=self._term_str(request.s),
                query_p=self._term_str(request.p),
                query_o=self._term_str(request.o),
                collection=request.collection or "",
                graph=request.g or "",
                workspace=workspace or "",
            )

        return filtered

    @staticmethod
    def _term_str(term):
        if term is None:
            return None
        if term.type == IRI:
            return term.iri
        if term.type == LITERAL:
            return term.value
        return None

    @staticmethod
    def add_args(parser):
        FlowProcessor.add_args(parser)


def run():
    Processor.launch(default_ident, __doc__)
