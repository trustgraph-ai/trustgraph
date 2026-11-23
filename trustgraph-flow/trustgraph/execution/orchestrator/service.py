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
    ExecutionState,
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
from ... base.serialization import dict_to_dataclass, dataclass_to_dict

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
            ConsumerSpec(
                name="step",
                schema=ExecutionState,
                handler=self.on_step,
                concurrency=concurrency,
            )
        )

        self.register_specification(
            ProducerSpec(
                name="step",
                schema=ExecutionState,
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
                    "emits": s.emits,
                }
                for s in planner_resp.steps
            ]

            statuses = {s.step_id: "pending" for s in planner_resp.steps}

            uc_str = ""
            if request.user_context:
                uc_str = json.dumps(dataclass_to_dict(request.user_context))

            state = ExecutionState(
                run_id=run_id,
                plan_id=plan_id,
                response_id=response_id,
                steps=json.dumps(steps_data),
                step_statuses=json.dumps(statuses),
                step_results=json.dumps({}),
                user_context=uc_str,
            )

            await flow("step").send(state)

            logger.info(f"Plan {plan_id} submitted for execution")

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

    async def on_step(self, msg, consumer, flow):

        try:

            state = msg.value()

            steps = json.loads(state.steps)
            statuses = json.loads(state.step_statuses)
            results = json.loads(state.step_results)
            user_context = None
            if state.user_context:
                from ... schema import UserContext
                user_context = dict_to_dataclass(
                    json.loads(state.user_context), UserContext,
                )

            ready = self._find_ready_steps(steps, statuses)

            if not ready:
                if all(s == "completed" for s in statuses.values()):
                    await self._send_response(
                        flow, state, results,
                    )
                else:
                    __class__.plan_fail_metric.labels(
                        processor=self.id, reason="deadlock",
                    ).inc()
                    await self._send_error(
                        flow, state.response_id, state.run_id,
                        state.plan_id, "orchestrator-error",
                        "No ready steps but plan is not complete",
                    )
                return

            logger.info(
                f"Executing {len(ready)} step(s) for plan "
                f"{state.plan_id}: "
                f"{[s['step-id'] for s in ready]}"
            )

            step_tasks = [
                self._execute_step(
                    flow, state, s, results, user_context,
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
                        flow, state.response_id, state.run_id,
                        state.plan_id, "step-failed",
                        f"Step {step_id} ({capability}) failed: "
                        f"{result}",
                    )
                    return

                artifact_type, artifact = result
                statuses[step_id] = "completed"
                results[step_id] = {
                    "artifact-type": artifact_type,
                    "artifact": artifact,
                }
                __class__.step_count_metric.labels(
                    processor=self.id, status="completed",
                ).inc()

            if all(s == "completed" for s in statuses.values()):
                await self._send_response(flow, state, results)
                return

            updated = ExecutionState(
                run_id=state.run_id,
                plan_id=state.plan_id,
                response_id=state.response_id,
                steps=state.steps,
                step_statuses=json.dumps(statuses),
                step_results=json.dumps(results),
                user_context=state.user_context,
            )

            await flow("step").send(updated)

        except Exception as e:

            logger.error(
                f"Exception in orchestrator step handler: {e}",
                exc_info=True,
            )

            try:
                await self._send_error(
                    flow, state.response_id, state.run_id,
                    state.plan_id, "orchestrator-error", str(e),
                )
            except Exception:
                logger.error("Failed to send error response", exc_info=True)

    async def _execute_step(
        self, flow, state, step, results, user_context,
    ):

        step_id = step["step-id"]
        capability = step["capability"]
        params = step.get("params", {})

        logger.info(
            f"Step {step_id}: {capability}"
        )

        t0 = time.monotonic()

        input_artifacts = self._resolve_input_artifacts(
            step, results,
        )

        policy = flow("policy-request")
        if policy:
            ingress = await policy.evaluate(
                run_id=state.run_id,
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
            run_id=state.run_id,
            step_id=step_id,
            capability=capability,
            params=params,
            input_artifacts=input_artifacts,
            user_context=user_context,
        )

        artifact_type = action_resp.artifact_type
        artifact = action_resp.artifact

        verification = flow("verification-request")
        if verification:
            ver_resp = await verification.verify(
                run_id=state.run_id,
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
                    f"Verification failed: {'; '.join(violations)}"
                )

        if policy:
            egress = await policy.evaluate(
                run_id=state.run_id,
                step_id=step_id,
                evaluation_type="step-egress",
                subject={
                    "type": artifact_type,
                    "capability": capability,
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
            f"{duration:.1f}s → {artifact_type}"
        )

        return artifact_type, artifact

    def _find_ready_steps(self, steps, statuses):
        ready = []
        for step in steps:
            step_id = step["step-id"]
            if statuses.get(step_id) != "pending":
                continue
            deps = step.get("depends-on", [])
            if all(statuses.get(d) == "completed" for d in deps):
                ready.append(step)
        return ready

    def _resolve_input_artifacts(self, step, results):
        input_artifacts = []
        for dep_id in step.get("depends-on", []):
            dep_result = results.get(dep_id)
            if dep_result:
                input_artifacts.append(dep_result)
        return input_artifacts

    async def _send_response(self, flow, state, results):

        artifacts = {}
        steps = json.loads(state.steps)
        for step in steps:
            step_id = step["step-id"]
            emits = step.get("emits", step_id)
            if step_id in results:
                artifacts[emits] = results[step_id]

        response = OrchestratorResponse(
            run_id=state.run_id,
            plan_id=state.plan_id,
            artifacts=artifacts,
        )

        await flow("response").send(
            response, properties={"id": state.response_id},
        )

        logger.info(
            f"Plan {state.plan_id} completed with "
            f"{len(artifacts)} artifacts"
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
