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


def _normalize_artifact_type(artifact_type):
    if isinstance(artifact_type, list):
        return " | ".join(artifact_type)
    return artifact_type


def prepare_capabilities(capabilities):
    result = []
    for cap in capabilities.values():
        prepared = {
            "name": cap.get("name", ""),
            "type": cap.get("type", "tool"),
            "description": cap.get("description", ""),
            "inputs": [
                {
                    "port": inp["port"],
                    "artifact_type": _normalize_artifact_type(
                        inp["artifact_type"],
                    ),
                    "optional": inp.get("optional", False),
                }
                for inp in cap.get("inputs", [])
            ],
            "outputs": [
                {
                    "port": out["port"],
                    "artifact_type": _normalize_artifact_type(
                        out["artifact_type"],
                    ),
                }
                for out in cap.get("outputs", [])
            ],
        }
        result.append(prepared)
    return result


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

        result = await flow("prompt-request").plan(
            goal=request.goal,
            capabilities=prepare_capabilities(capabilities),
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
            capability = str(item.get("capability", ""))
            cap = capabilities.get(capability)
            raw_params = item.get("params", {})

            params = {}
            for key, value in raw_params.items():
                if isinstance(value, str) and value.startswith("ref:"):
                    params[key] = value
                elif isinstance(value, str):
                    params[key] = self._wrap_literal(
                        capability, cap, key, value,
                    )
                elif isinstance(value, dict):
                    params[key] = value
                else:
                    params[key] = {
                        "artifact-type": "TextBlobArtifact",
                        "artifact": {"text": str(value)},
                    }

            step = ExecutionPlanStep(
                step_id=str(item.get("step_id", "")),
                capability=capability,
                depends_on=[
                    str(d) for d in item.get("depends_on", [])
                ],
                params=params,
            )
            steps.append(step)

        self.validate_plan(steps, capabilities)

        return steps

    def _wrap_literal(self, capability, cap, port_name, value):
        if cap is None:
            return {
                "artifact-type": "TextBlobArtifact",
                "artifact": {"text": value},
            }

        for inp in cap.get("inputs", []):
            if inp["port"] == port_name:
                artifact_type = inp["artifact_type"]
                if isinstance(artifact_type, list):
                    artifact_type = "TextBlobArtifact"
                if artifact_type == "TextBlobArtifact":
                    return {
                        "artifact-type": "TextBlobArtifact",
                        "artifact": {"text": value},
                    }
                logger.warning(
                    f"Capability {capability} port {port_name} "
                    f"expects {artifact_type} but got literal "
                    f"string '{value[:40]}...'"
                )
                return {
                    "artifact-type": "TextBlobArtifact",
                    "artifact": {"text": value},
                }

        return {
            "artifact-type": "TextBlobArtifact",
            "artifact": {"text": value},
        }

    def _get_output_type(self, capabilities, step_id, output_name, steps):
        for step in steps:
            if step.step_id != step_id:
                continue
            cap = capabilities.get(step.capability)
            if cap is None:
                return None
            for out in cap.get("outputs", []):
                if out["port"] == output_name:
                    return out["artifact_type"]
            return None
        return None

    def validate_plan(self, steps, capabilities):

        step_ids = {s.step_id for s in steps}

        for step in steps:
            cap = capabilities.get(step.capability)
            if cap is None:
                raise ValueError(
                    f"Step {step.step_id} references unknown "
                    f"capability '{step.capability}'"
                )

            for dep in step.depends_on:
                if dep not in step_ids:
                    raise ValueError(
                        f"Step {step.step_id} depends on unknown "
                        f"step '{dep}'"
                    )

            for key, value in step.params.items():
                if not isinstance(value, str):
                    continue
                if not value.startswith("ref:"):
                    continue

                parts = value[4:].split(":", 1)
                if len(parts) != 2:
                    raise ValueError(
                        f"Step {step.step_id}: invalid ref "
                        f"'{value}' — expected ref:STEP_ID:OUTPUT"
                    )

                ref_step_id, output_name = parts
                if ref_step_id not in step_ids:
                    raise ValueError(
                        f"Step {step.step_id}: ref '{value}' "
                        f"references unknown step '{ref_step_id}'"
                    )

                source_type = self._get_output_type(
                    capabilities, ref_step_id, output_name, steps,
                )
                if source_type is None:
                    raise ValueError(
                        f"Step {step.step_id}: ref '{value}' "
                        f"references unknown output "
                        f"'{output_name}' on step '{ref_step_id}'"
                    )

                expected_type = None
                for inp in cap.get("inputs", []):
                    if inp["port"] == key:
                        expected_type = inp["artifact_type"]
                        break

                if expected_type is not None:
                    self._check_type_compat(
                        step.step_id, key,
                        source_type, expected_type,
                    )

    def _check_type_compat(
        self, step_id, port, source_type, expected_type,
    ):
        if isinstance(source_type, list):
            source_set = set(source_type)
        else:
            source_set = {source_type}

        if isinstance(expected_type, list):
            expected_set = set(expected_type)
        else:
            expected_set = {expected_type}

        if not source_set & expected_set:
            raise ValueError(
                f"Step {step_id} port '{port}': source provides "
                f"{source_type} but input expects {expected_type}"
            )

    @staticmethod
    def add_args(parser):
        PlannerService.add_args(parser)


def run():
    Processor.launch(default_ident, __doc__)
