"""
Execution orchestrator.  Receives a goal, calls the planner to build a
DAG, then processes each step through policy checks, action execution,
and verification.  Uses self-invocation for step-level retry semantics:
each batch of ready steps is a separate message on a persistent queue.
"""

import asyncio
import json
import logging
import time
import uuid

from prometheus_client import Counter, Histogram

from ... schema import (
    OrchestratorRequest, OrchestratorResponse,
    Error,
)
from ... base import (
    FlowProcessor,
    ConsumerSpec,
    ProducerSpec,
    PlannerClientSpec,
    PolicyEngineClientSpec,
    ActionClientSpec,
    VerificationClientSpec,
)

logger = logging.getLogger(__name__)

default_ident = "orchestrator"
default_concurrency = 5


class Processor(FlowProcessor):

    def __init__(self, **params):

        concurrency = params.get("concurrency", default_concurrency)

        super(Processor, self).__init__(**params)

        self.register_specification(
            ConsumerSpec(
                name="request",
                schema=OrchestratorRequest,
                handler=self.on_request,
                concurrency=concurrency,
            )
        )

        self.register_specification(
            ProducerSpec(
                name="response",
                schema=OrchestratorResponse,
            )
        )

        self.register_specification(
            ProducerSpec(
                name="next",
                schema=OrchestratorRequest,
            )
        )

        self.register_specification(
            PlannerClientSpec(
                request_name="planner-request",
                response_name="planner-response",
            )
        )

        self.register_specification(
            PolicyEngineClientSpec(
                request_name="policy-request",
                response_name="policy-response",
                optional=True,
            )
        )

        self.register_specification(
            ActionClientSpec(
                request_name="action-request",
                response_name="action-response",
            )
        )

        self.register_specification(
            VerificationClientSpec(
                request_name="verification-request",
                response_name="verification-response",
                optional=True,
            )
        )

        if not hasattr(__class__, "orchestrator_duration_metric"):
            from ... base.metrics import BUCKETS_LLM
            __class__.orchestrator_duration_metric = Histogram(
                'tg_orchestrator_duration_seconds',
                'Orchestrator total execution latency',
                ["processor"],
                buckets=BUCKETS_LLM,
            )
            __class__.step_duration_metric = Histogram(
                'tg_orchestrator_step_duration_seconds',
                'Orchestrator per-step latency',
                ["processor", "capability"],
                buckets=BUCKETS_LLM,
            )
            __class__.step_count_metric = Counter(
                'tg_orchestrator_step_total',
                'Steps executed',
                ["processor", "status"],
            )
            __class__.plan_fail_metric = Counter(
                'tg_orchestrator_plan_fail_total',
                'Plans that failed',
                ["processor", "reason"],
            )

    async def on_request(self, msg, consumer, flow):

        t0 = time.monotonic()

        try:

            request = msg.value()
            response_id = msg.properties()["id"]

            if request.steps:
                await self._on_continuation(
                    request, response_id, flow, t0,
                )
            else:
                await self._on_new_goal(
                    request, response_id, flow, t0,
                )

        except Exception as e:

            logger.error(
                f"Exception in orchestrator request handler: {e}",
                exc_info=True,
            )

            try:
                response_id = msg.properties().get("id", "")
                await self._send_error(
                    flow, response_id, "", "",
                    "orchestrator-error", str(e),
                )
            except Exception:
                logger.error("Failed to send error response", exc_info=True)

    async def _on_new_goal(self, request, response_id, flow, t0):

        run_id = request.run_id or str(uuid.uuid4())

        logger.info(
            f"Orchestrator request {run_id}: {request.goal[:80]}..."
        )

        planner = flow("planner-request")

        planner_resp = await planner.plan(
            run_id=run_id,
            goal=request.goal,
            user_context=request.user_context,
        )

        if not planner_resp.steps:
            await self._send_error(
                flow, response_id, run_id, "",
                "planner-error", "Planner returned no steps",
            )
            return

        plan_id = planner_resp.plan_id or str(uuid.uuid4())

        logger.info(
            f"Plan {plan_id} has {len(planner_resp.steps)} steps"
        )

        policy = flow("policy-request")
        if policy:
            policy_resp = await policy.evaluate(
                run_id=run_id,
                step_id="",
                evaluation_type="plan-preflight",
                subject={
                    "type": "ExecutionPlan",
                    "step-count": len(planner_resp.steps),
                    "goal": request.goal,
                },
                user_context=request.user_context,
            )

            if policy_resp.verdict == "DENY":
                __class__.plan_fail_metric.labels(
                    processor=self.id, reason="policy-denied",
                ).inc()
                await self._send_error(
                    flow, response_id, run_id, plan_id,
                    "policy-denied",
                    f"Plan denied by policy: {policy_resp.message}",
                )
                return

        steps_data = [
            {
                "step-id": s.step_id,
                "capability": s.capability,
                "depends-on": s.depends_on,
                "params": s.params,
            }
            for s in planner_resp.steps
        ]

        statuses = {s.step_id: "pending" for s in planner_resp.steps}

        continuation = OrchestratorRequest(
            run_id=run_id,
            plan_id=plan_id,
            response_id=response_id,
            steps=json.dumps(steps_data),
            step_statuses=json.dumps(statuses),
            step_results=json.dumps({}),
            user_context=request.user_context,
        )

        await flow("next").send(
            continuation, properties={"id": response_id},
        )

        logger.info(f"Plan {plan_id} submitted for execution")

    async def _on_continuation(self, request, response_id, flow, t0):

        steps = json.loads(request.steps)
        statuses = json.loads(request.step_statuses)
        results = json.loads(request.step_results)

        ready = self._find_ready_steps(steps, statuses, results)

        if not ready:
            if all(s == "completed" for s in statuses.values()):
                await self._send_response(
                    flow, request, results,
                )
            else:
                __class__.plan_fail_metric.labels(
                    processor=self.id, reason="deadlock",
                ).inc()
                await self._send_error(
                    flow, request.response_id, request.run_id,
                    request.plan_id, "orchestrator-error",
                    "No ready steps but plan is not complete",
                )
            return

        logger.info(
            f"Executing {len(ready)} step(s) for plan "
            f"{request.plan_id}: "
            f"{[s['step-id'] for s in ready]}"
        )

        step_tasks = [
            self._execute_step(
                flow, request, s, results, request.user_context,
            )
            for s in ready
        ]

        step_results = await asyncio.gather(
            *step_tasks, return_exceptions=True,
        )

        for step, result in zip(ready, step_results):
            step_id = step["step-id"]
            capability = step["capability"]

            if isinstance(result, Exception):
                __class__.step_count_metric.labels(
                    processor=self.id, status="failed",
                ).inc()
                __class__.plan_fail_metric.labels(
                    processor=self.id, reason="step-failed",
                ).inc()
                logger.error(
                    f"Step {step_id} ({capability}) failed: "
                    f"{result}"
                )
                await self._send_error(
                    flow, request.response_id, request.run_id,
                    request.plan_id, "step-failed",
                    f"Step {step_id} ({capability}) failed: "
                    f"{result}",
                )
                return

            statuses[step_id] = "completed"
            results[step_id] = result
            __class__.step_count_metric.labels(
                processor=self.id, status="completed",
            ).inc()

        if all(s == "completed" for s in statuses.values()):
            await self._send_response(flow, request, results)
            return

        updated = OrchestratorRequest(
            run_id=request.run_id,
            plan_id=request.plan_id,
            response_id=request.response_id,
            steps=request.steps,
            step_statuses=json.dumps(statuses),
            step_results=json.dumps(results),
            user_context=request.user_context,
        )

        await flow("next").send(
            updated, properties={"id": request.response_id},
        )

    async def _execute_step(
        self, flow, request, step, results, user_context,
    ):

        step_id = step["step-id"]
        capability = step["capability"]
        raw_params = step.get("params", {})

        logger.info(
            f"Step {step_id}: {capability}"
        )

        t0 = time.monotonic()

        resolved = self._resolve_params(raw_params, results)

        policy = flow("policy-request")
        if policy:
            ingress = await policy.evaluate(
                run_id=request.run_id,
                step_id=step_id,
                evaluation_type="step-ingress",
                subject={
                    "type": "Step",
                    "capability": capability,
                },
                user_context=user_context,
            )

            if ingress.verdict == "DENY":
                raise RuntimeError(
                    f"Step denied by ingress policy: {ingress.message}"
                )

        action = flow("action-request")
        action_resp = await action.execute(
            run_id=request.run_id,
            step_id=step_id,
            capability=capability,
            params=json.dumps(resolved),
            user_context=user_context,
        )

        artifacts = json.loads(action_resp.artifacts) if action_resp.artifacts else {}

        verification = flow("verification-request")
        if verification:
            for name, entry in artifacts.items():
                artifact_type = entry.get("artifact-type", "")
                artifact = entry.get("artifact", {})
                ver_resp = await verification.verify(
                    run_id=request.run_id,
                    step_id=step_id,
                    expected_type=artifact_type,
                    artifact=artifact,
                )

                if not ver_resp.valid:
                    violations = [
                        f"[{v.severity}] {v.field}: {v.message}"
                        for v in ver_resp.violations
                    ]
                    raise RuntimeError(
                        f"Verification failed for {name}: "
                        f"{'; '.join(violations)}"
                    )

        if policy:
            artifact_types = [
                e.get("artifact-type", "") for e in artifacts.values()
            ]
            egress = await policy.evaluate(
                run_id=request.run_id,
                step_id=step_id,
                evaluation_type="step-egress",
                subject={
                    "type": "StepOutputs",
                    "capability": capability,
                    "artifact-types": artifact_types,
                },
                user_context=user_context,
            )

            if egress.verdict == "DENY":
                raise RuntimeError(
                    f"Step denied by egress policy: {egress.message}"
                )

        duration = time.monotonic() - t0
        __class__.step_duration_metric.labels(
            processor=self.id, capability=capability,
        ).observe(duration)

        logger.info(
            f"Step {step_id} ({capability}) completed in "
            f"{duration:.1f}s → "
            f"{[e.get('artifact-type') for e in artifacts.values()]}"
        )

        return artifacts

    def _find_ready_steps(self, steps, statuses, results):
        ready = []
        for step in steps:
            step_id = step["step-id"]
            if statuses.get(step_id) != "pending":
                continue

            deps = set(step.get("depends-on", []))

            for value in step.get("params", {}).values():
                if isinstance(value, str) and value.startswith("ref:"):
                    parts = value[4:].split(":", 1)
                    if len(parts) == 2:
                        deps.add(parts[0])

            if all(statuses.get(d) == "completed" for d in deps):
                ready.append(step)
        return ready

    def _resolve_params(self, raw_params, results):
        resolved = {}
        for key, value in raw_params.items():
            if isinstance(value, str) and value.startswith("ref:"):
                parts = value[4:].split(":", 1)
                if len(parts) != 2:
                    raise RuntimeError(
                        f"Invalid ref parameter '{value}': "
                        f"expected 'ref:STEP_ID:OUTPUT_NAME'"
                    )
                ref_step_id, output_name = parts
                step_result = results.get(ref_step_id)
                if step_result is None:
                    raise RuntimeError(
                        f"ref parameter '{value}' references "
                        f"step '{ref_step_id}' which has no result"
                    )
                artifact = step_result.get(output_name)
                if artifact is None:
                    raise RuntimeError(
                        f"ref parameter '{value}' references "
                        f"output '{output_name}' not found in "
                        f"step '{ref_step_id}'"
                    )
                resolved[key] = artifact
            elif isinstance(value, dict):
                resolved[key] = value
            else:
                raise RuntimeError(
                    f"Unexpected param value for '{key}': "
                    f"expected artifact dict or ref: string, "
                    f"got {type(value).__name__}"
                )
        return resolved

    async def _send_response(self, flow, request, results):

        response = OrchestratorResponse(
            run_id=request.run_id,
            plan_id=request.plan_id,
            artifacts=results,
        )

        await flow("response").send(
            response, properties={"id": request.response_id},
        )

        artifact_count = sum(len(v) for v in results.values())
        logger.info(
            f"Plan {request.plan_id} completed with "
            f"{artifact_count} artifacts from {len(results)} steps"
        )

    async def _send_error(
        self, flow, response_id, run_id, plan_id, error_type, message,
    ):

        logger.error(f"Plan failed [{error_type}]: {message}")

        response = OrchestratorResponse(
            run_id=run_id,
            plan_id=plan_id,
            error=Error(type=error_type, message=message),
        )

        await flow("response").send(
            response, properties={"id": response_id},
        )

    @staticmethod
    def add_args(parser):
        FlowProcessor.add_args(parser)


def run():
    Processor.launch(default_ident, __doc__)
