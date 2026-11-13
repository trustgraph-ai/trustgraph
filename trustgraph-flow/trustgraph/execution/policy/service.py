"""
Policy engine service.  Evaluates plans, steps, and artifacts against
SHACL-AF policy rules loaded from config.  Returns attestations with
verdict, disclosure posture, and optional redaction directives.
"""

import logging

from ... schema import (
    PolicyEngineRequest, PolicyEngineResponse, RedactionDirective,
)
from ... base import PolicyEngineService

from . evaluator import parse_rules, evaluate_rules

logger = logging.getLogger(__name__)

default_ident = "policy"


class Processor(PolicyEngineService):

    def __init__(self, **params):

        super(Processor, self).__init__(**params)

        self.register_config_handler(
            self.on_policy_config,
            types=["execution-policy-rule"],
        )

        self.rules = {}

    async def on_policy_config(self, workspace, config, version):

        logger.info(
            f"Loading execution policy rules for workspace {workspace} "
            f"(version {version})"
        )

        rule_config = config.get("execution-policy-rule", {})

        all_rules = []
        for key, value in rule_config.items():
            try:
                parsed = parse_rules(value)
                all_rules.extend(parsed)
                logger.info(
                    f"Loaded policy rule '{key}' "
                    f"({len(parsed)} shapes)"
                )
            except Exception as e:
                logger.error(
                    f"Failed to parse policy rule '{key}': {e}"
                )

        all_rules.sort(key=lambda r: r.order)

        self.rules[workspace] = all_rules

        logger.info(
            f"Policy engine has {len(all_rules)} rules "
            f"for workspace {workspace}"
        )

    async def evaluate(self, workspace, request, flow):

        rules = self.rules.get(workspace, [])

        if not rules:
            logger.debug(
                f"No policy rules for workspace {workspace}, "
                f"defaulting to ALLOW"
            )
            return PolicyEngineResponse(
                run_id=request.run_id,
                step_id=request.step_id,
                verdict="ALLOW",
                disclosure="SILENT",
                boundary_failure=False,
                message="No policy rules configured",
            )

        logger.info(
            f"Evaluating {request.evaluation_type} for "
            f"run {request.run_id} step {request.step_id}"
        )

        result = evaluate_rules(
            rules,
            request.evaluation_type,
            request.subject,
            request.principal,
        )

        matched_rules = []
        if result.get("matched_rule"):
            matched_rules.append(result["matched_rule"])

        redaction_directives = [
            RedactionDirective(
                field=rd["field"],
                method=rd["method"],
                rule_id=result.get("matched_rule", ""),
            )
            for rd in result.get("redaction_fields", [])
        ]

        logger.info(
            f"Policy verdict for run {request.run_id} "
            f"step {request.step_id}: {result['verdict']}"
        )

        return PolicyEngineResponse(
            run_id=request.run_id,
            step_id=request.step_id,
            verdict=result["verdict"],
            disclosure=result["disclosure"],
            boundary_failure=result["boundary_failure"],
            matched_rules=matched_rules,
            redaction_directives=redaction_directives,
            message=result.get("message", ""),
        )

    @staticmethod
    def add_args(parser):
        PolicyEngineService.add_args(parser)


def run():
    Processor.launch(default_ident, __doc__)
