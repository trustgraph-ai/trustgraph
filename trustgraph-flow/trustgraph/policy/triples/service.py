
"""
Policy-filtered triples query service.

Same input interface as triples-query, but applies SHACL-AF policy
filtering to the response. Delegates the actual graph query to the
backing triples-query service via RPC.

Flow config selects between triples-query (no policy) and this
service.
"""

import time
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
from .. policy_filter import (
    PolicyFilter, QueryCache, SparqlCache, NodeDeterminationCache,
)

logger = logging.getLogger(__name__)

default_ident = "triples-policy"
default_concurrency = 20
POLICY_CACHE_TTL = 60


class Processor(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id", default_ident)
        concurrency = params.get("concurrency", default_concurrency)

        super(Processor, self).__init__(
            **params | {"id": id}
        )

        self._query_caches = {}
        self._sparql_cache = SparqlCache()
        self._node_cache = NodeDeterminationCache()
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

            needs_policy = await self._needs_policy(
                request, workspace, triples_client,
            )

            if needs_policy is None:
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

            if not needs_policy:
                await self._passthrough(
                    request, triples_client, flow, id,
                )
                return

            await self._filtered_query(
                request, workspace, triples_client, flow, id,
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

    async def _needs_policy(self, request, workspace, triples_client):
        """Check whether policy filtering is needed.

        Returns:
            True  — policies exist and user_context is provided, filter
            False — no filtering needed, pass through
            None  — policies exist but no user_context (reject)
        """
        async def query_fn(s, p, o, collection, g=""):
            results = []
            async def collect(resp):
                if resp.error:
                    raise RuntimeError(resp.error.message)
                if resp.triples:
                    results.extend(resp.triples)
                return resp.is_final
            await triples_client.request(
                TriplesQueryRequest(
                    s=s, p=p, o=o,
                    collection=collection, g=g,
                    limit=10000, streaming=True,
                ),
                recipient=collect,
            )
            return results

        if workspace not in self._query_caches:
            self._query_caches[workspace] = QueryCache(query_fn)

        collection = request.collection or "default"
        policy_key = (workspace, collection)
        cached = self._policy_cache.get(policy_key)
        now = time.monotonic()

        if cached is not None and now - cached[2] >= POLICY_CACHE_TTL:
            del self._policy_cache[policy_key]
            cached = None

        if cached is None:
            policy_filter = PolicyFilter(
                query_fn=query_fn,
                query_cache=self._query_caches[workspace],
                sparql_cache=self._sparql_cache,
            )
            await policy_filter.load_policies(collection)
            self._policy_cache[policy_key] = (
                policy_filter._policies or [],
                policy_filter._required_predicates,
                now,
            )
            cached = self._policy_cache[policy_key]

        has_policies = bool(cached[0])

        if has_policies and not request.user_context:
            return None

        if not request.user_context:
            return False

        return has_policies

    async def _passthrough(self, request, triples_client, flow, id):
        """Forward request to backend as-is, preserving streaming."""

        async def relay(resp):
            await flow("response").send(resp, properties={"id": id})
            return resp.is_final

        await triples_client.request(request, recipient=relay)

    async def _filtered_query(self, request, workspace, triples_client,
                              flow, id):
        """Stream triples from backend, filter each batch, relay."""

        evaluations = []

        async def on_evaluation(ev):
            evaluations.append(ev)

        async def query_fn(s, p, o, collection, g=""):
            results = []
            async def collect(resp):
                if resp.error:
                    raise RuntimeError(resp.error.message)
                if resp.triples:
                    results.extend(resp.triples)
                return resp.is_final
            await triples_client.request(
                TriplesQueryRequest(
                    s=s, p=p, o=o,
                    collection=collection, g=g,
                    limit=10000, streaming=True,
                ),
                recipient=collect,
            )
            return results

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
            node_cache=self._node_cache,
            policies=policies,
            required_predicates=required_predicates,
        )

        await policy_filter.load_policies(collection)

        if policy_key not in self._policy_cache and policy_filter._policies:
            self._policy_cache[policy_key] = (
                policy_filter._policies,
                policy_filter._required_predicates,
                time.monotonic(),
            )

        sent_any = False

        async def relay(resp):
            nonlocal sent_any

            if resp.error:
                await flow("response").send(
                    TriplesQueryResponse(error=resp.error, triples=None),
                    properties={"id": id},
                )
                return resp.is_final

            triples = resp.triples or []

            filtered = await policy_filter.apply(
                triples, collection, request.user_context,
                graph=request.g,
            )

            if filtered:
                sent_any = True
                r = TriplesQueryResponse(
                    triples=filtered, error=None,
                    is_final=resp.is_final,
                )
                await flow("response").send(r, properties={"id": id})
            elif resp.is_final:
                r = TriplesQueryResponse(
                    triples=[], error=None, is_final=True,
                )
                await flow("response").send(r, properties={"id": id})

            return resp.is_final

        await triples_client.request(request, recipient=relay)

        if not sent_any:
            r = TriplesQueryResponse(
                triples=[], error=None, is_final=True,
            )
            await flow("response").send(r, properties={"id": id})

        if evaluations:
            await self.policy_event_publisher.emit_evaluations(
                evaluations=evaluations,
                user_context=request.user_context,
                request_id=str(uuid4()),
                query_s=self._term_str(request.s),
                query_p=self._term_str(request.p),
                query_o=self._term_str(request.o),
                collection=collection,
                graph=request.g or "",
                workspace=workspace or "",
            )

        logger.debug("Policy-filtered triples query completed")

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
