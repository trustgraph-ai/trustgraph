"""
MetaRouter — selects the task type and execution pattern for a query.

Uses the config API to look up available task types and patterns, then
asks the LLM to classify the query and select the best pattern.
Falls back to ("react", "general", "") if config is empty.
"""

import json
import logging

logger = logging.getLogger(__name__)

DEFAULT_PATTERN = "react"
DEFAULT_TASK_TYPE = "general"
DEFAULT_FRAMING = ""


class MetaRouter:

    def __init__(self, config=None):
        """
        Args:
            config: The full config dict from the config service.
                    May contain "agent-pattern" and "agent-task-type" keys.
        """
        self.patterns = {}
        self.task_types = {}

        if config:
            # Load from config API
            if "agent-pattern" in config:
                for pid, pval in config["agent-pattern"].items():
                    try:
                        self.patterns[pid] = json.loads(pval)
                    except (json.JSONDecodeError, TypeError):
                        self.patterns[pid] = {"name": pid}

            if "agent-task-type" in config:
                for tid, tval in config["agent-task-type"].items():
                    try:
                        self.task_types[tid] = json.loads(tval)
                    except (json.JSONDecodeError, TypeError):
                        self.task_types[tid] = {"name": tid}

        # If config has no patterns/task-types, default to react/general
        if not self.patterns:
            self.patterns = {
                "react": {"name": "react", "description": "Interleaved reasoning and action"},
            }
        if not self.task_types:
            self.task_types = {
                "general": {"name": "general", "description": "General queries", "valid_patterns": ["react"], "framing": ""},
            }

    async def identify_task_type(self, question, context, usage=None):
        """
        Use the LLM to classify the question into one of the known task types.

        Args:
            question: The user's query.
            context: UserAwareContext (flow wrapper).

        Returns:
            (task_type_id, framing) tuple.
        """
        if len(self.task_types) <= 1:
            tid = next(iter(self.task_types), DEFAULT_TASK_TYPE)
            framing = self.task_types.get(tid, {}).get("framing", DEFAULT_FRAMING)
            return tid, framing

        try:
            client = context("prompt-request")
            result = await client.prompt(
                id="task-type-classify",
                variables={
                    "question": question,
                    "task_types": [
                        {"name": tid, "description": tdata.get("description", tid)}
                        for tid, tdata in self.task_types.items()
                    ],
                },
            )
            if usage:
                usage.track(result)
            selected = result.text.strip().lower().replace('"', '').replace("'", "")

            if selected in self.task_types:
                framing = self.task_types[selected].get("framing", DEFAULT_FRAMING)
                logger.info(f"MetaRouter: identified task type '{selected}'")
                return selected, framing
            else:
                logger.warning(
                    f"MetaRouter: LLM returned unknown task type '{selected}', "
                    f"falling back to '{DEFAULT_TASK_TYPE}'"
                )
        except Exception as e:
            logger.warning(f"MetaRouter: task type classification failed: {e}")

        framing = self.task_types.get(DEFAULT_TASK_TYPE, {}).get(
            "framing", DEFAULT_FRAMING
        )
        return DEFAULT_TASK_TYPE, framing

    async def select_pattern(self, question, task_type, context, usage=None):
        """
        Use the LLM to select the best execution pattern for this task type.

        Args:
            question: The user's query.
            task_type: The identified task type ID.
            context: UserAwareContext (flow wrapper).

        Returns:
            Pattern ID string.
        """
        task_config = self.task_types.get(task_type, {})
        valid_patterns = task_config.get("valid_patterns", list(self.patterns.keys()))

        if len(valid_patterns) <= 1:
            return valid_patterns[0] if valid_patterns else DEFAULT_PATTERN

        try:
            client = context("prompt-request")
            result = await client.prompt(
                id="pattern-select",
                variables={
                    "question": question,
                    "task_type": task_type,
                    "task_type_description": task_config.get("description", task_type),
                    "patterns": [
                        {"name": pid, "description": self.patterns.get(pid, {}).get("description", pid)}
                        for pid in valid_patterns
                        if pid in self.patterns
                    ],
                },
            )
            if usage:
                usage.track(result)
            selected = result.text.strip().lower().replace('"', '').replace("'", "")

            if selected in valid_patterns:
                logger.info(f"MetaRouter: selected pattern '{selected}'")
                return selected
            else:
                logger.warning(
                    f"MetaRouter: LLM returned invalid pattern '{selected}', "
                    f"falling back to '{valid_patterns[0]}'"
                )
                return valid_patterns[0]
        except Exception as e:
            logger.warning(f"MetaRouter: pattern selection failed: {e}")
            return valid_patterns[0] if valid_patterns else DEFAULT_PATTERN

    async def route(self, question, context, usage=None):
        """
        Full routing pipeline: identify task type, then select pattern.

        Args:
            question: The user's query.
            context: UserAwareContext (flow wrapper).
            usage: Optional UsageTracker for token counting.

        Returns:
            (pattern, task_type, framing) tuple.
        """
        task_type, framing = await self.identify_task_type(question, context, usage=usage)
        pattern = await self.select_pattern(question, task_type, context, usage=usage)
        logger.info(
            f"MetaRouter: route result — "
            f"pattern={pattern}, task_type={task_type}, framing={framing!r}"
        )
        return pattern, task_type, framing
