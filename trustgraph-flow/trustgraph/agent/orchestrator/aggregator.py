"""
Aggregator — tracks in-flight fan-out correlations and triggers
synthesis when all subagents have completed.

Subagent completions arrive as AgentRequest messages on the agent
request queue with step_type="subagent-completion". The orchestrator
intercepts these and feeds them to the aggregator. When all expected
siblings for a correlation ID have reported, the aggregator builds
a synthesis request for the supervisor pattern.
"""

import asyncio
import json
import logging
import time
import uuid

from ... schema import AgentRequest, AgentStep

logger = logging.getLogger(__name__)

# How long to wait for stalled correlations before giving up (seconds)
DEFAULT_TIMEOUT = 300


class Aggregator:
    """
    Tracks in-flight fan-out correlations and triggers synthesis
    when all subagents complete.

    State is held in-memory; if the process restarts, in-flight
    correlations are lost (acceptable for v1).
    """

    def __init__(self, timeout=DEFAULT_TIMEOUT):
        self.timeout = timeout

        # correlation_id -> {
        #   "parent_session_id": str,
        #   "expected": int,
        #   "results": {goal: answer},
        #   "request_template": AgentRequest or None,
        #   "created_at": float,
        # }
        self.correlations = {}

    def register_fanout(self, correlation_id, parent_session_id,
                        expected_siblings, request_template=None):
        """
        Register a new fan-out. Called by the supervisor after emitting
        subagent requests.
        """
        self.correlations[correlation_id] = {
            "parent_session_id": parent_session_id,
            "expected": expected_siblings,
            "results": {},
            "request_template": request_template,
            "created_at": time.time(),
        }
        logger.debug(
            f"Aggregator: registered fan-out {correlation_id}, "
            f"expecting {expected_siblings} subagents"
        )

    def record_completion(self, correlation_id, subagent_goal, result):
        """
        Record a subagent completion.

        Returns:
            True if all siblings are now complete, False otherwise.
            Returns None if the correlation_id is unknown.
        """
        if correlation_id not in self.correlations:
            logger.warning(
                f"Aggregator: unknown correlation_id {correlation_id}"
            )
            return None

        entry = self.correlations[correlation_id]
        entry["results"][subagent_goal] = result

        completed = len(entry["results"])
        expected = entry["expected"]

        logger.debug(
            f"Aggregator: {correlation_id} — "
            f"{completed}/{expected} subagents complete"
        )

        return completed >= expected

    def get_original_request(self, correlation_id):
        """Peek at the stored request template without consuming it."""
        entry = self.correlations.get(correlation_id)
        if entry is None:
            return None
        return entry["request_template"]

    def get_results(self, correlation_id):
        """Get all results for a correlation and remove the tracking entry."""
        entry = self.correlations.pop(correlation_id, None)
        if entry is None:
            return None, None, None
        return (
            entry["results"],
            entry["parent_session_id"],
            entry["request_template"],
        )

    def build_synthesis_request(self, correlation_id, original_question,
                                user, collection):
        """
        Build the AgentRequest that triggers the synthesis phase.
        """
        results, parent_session_id, template = self.get_results(correlation_id)

        if results is None:
            raise RuntimeError(
                f"No results for correlation_id {correlation_id}"
            )

        # Build history with decompose step + results
        synthesis_step = AgentStep(
            thought="All subagents completed",
            action="aggregate",
            arguments={},
            observation=json.dumps(results),
            step_type="synthesise",
            subagent_results=results,
        )

        history = []
        if template and template.history:
            history = list(template.history)
        history.append(synthesis_step)

        return AgentRequest(
            question=original_question,
            state="",
            group=template.group if template else [],
            history=history,
            user=user,
            collection=collection,
            streaming=template.streaming if template else False,
            session_id=parent_session_id,
            conversation_id=template.conversation_id if template else "",
            pattern="supervisor",
            task_type=template.task_type if template else "",
            framing=template.framing if template else "",
            correlation_id="",
            parent_session_id="",
            subagent_goal="",
            expected_siblings=0,
        )

    def cleanup_stale(self):
        """Remove correlations that have timed out."""
        now = time.time()
        stale = [
            cid for cid, entry in self.correlations.items()
            if now - entry["created_at"] > self.timeout
        ]
        for cid in stale:
            logger.warning(f"Aggregator: timing out stale correlation {cid}")
            self.correlations.pop(cid, None)
        return stale
