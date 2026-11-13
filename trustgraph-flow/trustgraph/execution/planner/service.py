"""
Execution planner service.  Decomposes a goal into an execution plan
DAG using the prompt service and a capability registry loaded from
config.
"""

import json
import logging
import uuid

from ... schema import PlannerRequest, PlannerResponse, ExecutionPlanStep, Error
from ... base import PlannerService, PromptClientSpec

logger = logging.getLogger(__name__)

default_ident = "planner"


def format_capabilities(capabilities):
    lines = []
    for cap in capabilities.values():
        lines.append(f"  {cap['name']} ({cap.get('type', 'tool')})")
        lines.append(f"    {cap.get('description', '')}")
        inputs = cap.get("inputs", [])
        if inputs:
            inp_str = ", ".join(
                f"{p['port']}: {p['artifact_type']}"
                for p in inputs
            )
            lines.append(f"    Inputs: {inp_str}")
        else:
            lines.append(
                "    Inputs: none (source — query passed as parameter)"
            )
        outputs = cap.get("outputs", [])
        out_str = ", ".join(
            f"{p['port']}: {p['artifact_type']}"
            for p in outputs
        )
        lines.append(f"    Outputs: {out_str}")
        lines.append("")
    return "\n".join(lines)


class Processor(PlannerService):

    def __init__(self, **params):

        super(Processor, self).__init__(**params)

        self.register_specification(
            PromptClientSpec(
                request_name="prompt-request",
                response_name="prompt-response",
            )
        )

        self.register_config_handler(
            self.on_capability_config,
            types=["planner-capability"],
        )

        self.capabilities = {}

    async def on_capability_config(self, workspace, config, version):

        logger.info(
            f"Loading planner capabilities for workspace {workspace} "
            f"(version {version})"
        )

        cap_config = config.get("planner-capability", {})

        capabilities = {}
        for key, value in cap_config.items():
            try:
                cap = json.loads(value)
                if "name" not in cap:
                    cap["name"] = key
                capabilities[key] = cap
                logger.info(f"Loaded capability '{key}'")
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(
                    f"Failed to load capability '{key}': {e}"
                )

        self.capabilities[workspace] = capabilities

        logger.info(
            f"Planner has {len(capabilities)} capabilities "
            f"for workspace {workspace}"
        )

    async def create_plan(self, workspace, request, flow):

        capabilities = self.capabilities.get(workspace, {})

        if not capabilities:
            raise RuntimeError(
                "No planner capabilities configured for this workspace"
            )

        logger.info(
            f"Planning for run {request.run_id}: {request.goal[:80]}..."
        )

        capability_text = format_capabilities(capabilities)

        result = await flow("prompt-request").plan(
            goal=request.goal,
            capabilities=capability_text,
        )

        steps = self.parse_plan(result.objects, capabilities)

        plan_id = f"plan-{uuid.uuid4().hex[:8]}"

        logger.info(
            f"Plan {plan_id} for run {request.run_id}: "
            f"{len(steps)} steps"
        )

        return PlannerResponse(
            run_id=request.run_id,
            plan_id=plan_id,
            steps=steps,
        )

    def parse_plan(self, raw, capabilities):

        if not isinstance(raw, list):
            raise ValueError(
                f"Expected JSON array, got {type(raw).__name__}"
            )

        steps = []
        for item in raw:
            step = ExecutionPlanStep(
                step_id=str(item.get("step_id", "")),
                capability=str(item.get("capability", "")),
                depends_on=[
                    str(d) for d in item.get("depends_on", [])
                ],
                params={
                    str(k): str(v)
                    for k, v in item.get("params", {}).items()
                },
                emits=str(item.get("emits", "")),
            )
            steps.append(step)

        self.validate_plan(steps, capabilities)

        return steps

    def validate_plan(self, steps, capabilities):

        step_ids = {s.step_id for s in steps}

        step_outputs = {}
        for step in steps:
            cap = capabilities.get(step.capability)
            if cap is None:
                raise ValueError(
                    f"Step {step.step_id} references unknown "
                    f"capability '{step.capability}'"
                )
            outputs = cap.get("outputs", [])
            if outputs:
                step_outputs[step.step_id] = outputs[0]["artifact_type"]

        for step in steps:
            for dep in step.depends_on:
                if dep not in step_ids:
                    raise ValueError(
                        f"Step {step.step_id} depends on unknown "
                        f"step '{dep}'"
                    )

            cap = capabilities[step.capability]
            required_inputs = cap.get("inputs", [])
            dep_types = [
                step_outputs.get(d) for d in step.depends_on
            ]

            for port in required_inputs:
                expected = port["artifact_type"]
                if expected not in dep_types:
                    raise ValueError(
                        f"Step {step.step_id} ({step.capability}) "
                        f"requires input {port['port']}: {expected} "
                        f"but dependencies provide: "
                        f"{dep_types}"
                    )

    @staticmethod
    def add_args(parser):
        PlannerService.add_args(parser)


def run():
    Processor.launch(default_ident, __doc__)
