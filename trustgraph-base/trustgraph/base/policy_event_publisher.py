
import json
import logging
from datetime import datetime, timezone
from uuid import uuid4
from collections import defaultdict

from trustgraph.schema import PolicyEvent, policy_events_queue

logger = logging.getLogger(__name__)

NODE_IRI_CAP = 100

EVENT_TYPE_MAP = {
    "Notify": "policy.notify",
    "Filtered": "policy.filtered",
    "Violation": "policy.violation",
}


class PolicyEventPublisher:

    def __init__(self, component_name, async_backend=None):
        self.component_name = component_name
        self._handle = None
        self._async_producer = None
        self._async_backend = async_backend

    async def start(self, sender_pool=None):
        if sender_pool is not None:
            self._handle = await sender_pool.add_producer(
                topic=policy_events_queue,
                schema=PolicyEvent,
            )
        elif self._async_backend is not None:
            self._async_producer = (
                await self._async_backend.create_producer(
                    topic=policy_events_queue,
                    schema=PolicyEvent,
                )
            )

    async def stop(self):
        if self._async_producer:
            try:
                await self._async_producer.close()
            except BaseException:
                pass
            self._async_producer = None
        if self._handle:
            await self._handle.unregister()

    async def emit(self, event_type, payload):
        event = PolicyEvent(
            schema_version=1,
            event_id=str(uuid4()),
            event_type=event_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            producer=self.component_name,
            payload_json=json.dumps(payload),
        )

        try:
            if self._handle:
                await self._handle.send(event)
            elif self._async_producer:
                await self._async_producer.send(event)
        except Exception as e:
            logger.warning(f"Failed to emit policy event: {e}")

    async def emit_evaluations(
        self,
        evaluations,
        user_context,
        query_s=None,
        query_p=None,
        query_o=None,
        collection="",
        graph="",
        workspace="",
    ):
        """Batch evaluations by policy and emit one event per policy.

        Evaluations with the same policy_uri are grouped into a single
        event. The node_iris list is capped at NODE_IRI_CAP per event;
        node_count always reflects the true total.
        """

        by_policy = defaultdict(list)
        for ev in evaluations:
            by_policy[(ev.policy_uri, ev.policy_label,
                       ev.determination)].append(ev)

        for (policy_uri, policy_label, determination), group in (
            by_policy.items()
        ):
            node_iris = [ev.node_iri for ev in group]
            node_count = len(node_iris)

            event_type = EVENT_TYPE_MAP.get(
                determination, "policy.notify",
            )

            payload = {
                "policy_uri": policy_uri,
                "policy_label": policy_label,
                "determination": determination,
                "user_context": self._serialise_user_context(
                    user_context
                ),
                "node_iris": node_iris[:NODE_IRI_CAP],
                "node_count": node_count,
                "query_s": query_s,
                "query_p": query_p,
                "query_o": query_o,
                "collection": collection,
                "graph": graph,
                "workspace": workspace,
            }

            await self.emit(event_type, payload)

    def _serialise_user_context(self, user_context):
        if user_context is None:
            return None

        result = {
            "user_id": user_context.user_id,
            "roles": user_context.roles,
            "organisational_units": user_context.organisational_units,
            "purpose": user_context.purpose,
        }

        if user_context.assignments:
            result["assignments"] = [
                {
                    "resource": a.resource,
                    "scope": a.scope,
                    "status": a.status,
                    "valid_from": a.valid_from,
                    "valid_to": a.valid_to,
                    "qualifiers": a.qualifiers,
                }
                for a in user_context.assignments
            ]

        if user_context.entitlements:
            result["entitlements"] = [
                {
                    "resource_scope": e.resource_scope,
                    "access_level": e.access_level,
                    "valid_from": e.valid_from,
                    "valid_to": e.valid_to,
                }
                for e in user_context.entitlements
            ]

        if user_context.override_authorities:
            result["override_authorities"] = [
                {
                    "policy_area": oa.policy_area,
                    "condition": oa.condition,
                }
                for oa in user_context.override_authorities
            ]

        if user_context.delegation:
            result["delegation"] = {
                "delegator_id": user_context.delegation.delegator_id,
                "scope": user_context.delegation.scope,
            }

        return result
