"""
Unit tests for the MetaRouter — task type identification and pattern selection.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from trustgraph.agent.orchestrator.meta_router import (
    MetaRouter, DEFAULT_PATTERN, DEFAULT_TASK_TYPE,
)


def _make_config(patterns=None, task_types=None):
    """Build a config dict as the config service would provide."""
    config = {}
    if patterns:
        config["agent-pattern"] = {
            pid: json.dumps(pdata) for pid, pdata in patterns.items()
        }
    if task_types:
        config["agent-task-type"] = {
            tid: json.dumps(tdata) for tid, tdata in task_types.items()
        }
    return config


def _make_context(prompt_response):
    """Build a mock context that returns a mock prompt client."""
    client = AsyncMock()
    client.prompt = AsyncMock(return_value=prompt_response)

    def context(service_name):
        return client

    return context


SAMPLE_PATTERNS = {
    "react": {"name": "react", "description": "ReAct pattern"},
    "plan-then-execute": {"name": "plan-then-execute", "description": "Plan pattern"},
    "supervisor": {"name": "supervisor", "description": "Supervisor pattern"},
}

SAMPLE_TASK_TYPES = {
    "general": {
        "name": "general",
        "description": "General queries",
        "valid_patterns": ["react", "plan-then-execute", "supervisor"],
        "framing": "",
    },
    "research": {
        "name": "research",
        "description": "Research queries",
        "valid_patterns": ["react", "plan-then-execute"],
        "framing": "Focus on gathering information.",
    },
    "summarisation": {
        "name": "summarisation",
        "description": "Summarisation queries",
        "valid_patterns": ["react"],
        "framing": "Focus on concise synthesis.",
    },
}


class TestMetaRouterInit:

    def test_defaults_when_no_config(self):
        router = MetaRouter()
        assert "react" in router.patterns
        assert "general" in router.task_types

    def test_loads_patterns_from_config(self):
        config = _make_config(patterns=SAMPLE_PATTERNS)
        router = MetaRouter(config=config)
        assert set(router.patterns.keys()) == {"react", "plan-then-execute", "supervisor"}

    def test_loads_task_types_from_config(self):
        config = _make_config(task_types=SAMPLE_TASK_TYPES)
        router = MetaRouter(config=config)
        assert set(router.task_types.keys()) == {"general", "research", "summarisation"}

    def test_handles_invalid_json_in_config(self):
        config = {
            "agent-pattern": {"react": "not valid json"},
        }
        router = MetaRouter(config=config)
        assert "react" in router.patterns
        assert router.patterns["react"]["name"] == "react"


class TestIdentifyTaskType:

    @pytest.mark.asyncio
    async def test_skips_llm_when_single_task_type(self):
        router = MetaRouter()  # Only "general"
        context = _make_context("should not be called")

        task_type, framing = await router.identify_task_type(
            "test question", context,
        )

        assert task_type == "general"

    @pytest.mark.asyncio
    async def test_uses_llm_when_multiple_task_types(self):
        config = _make_config(
            patterns=SAMPLE_PATTERNS,
            task_types=SAMPLE_TASK_TYPES,
        )
        router = MetaRouter(config=config)
        context = _make_context("research")

        task_type, framing = await router.identify_task_type(
            "Research the topic", context,
        )

        assert task_type == "research"
        assert framing == "Focus on gathering information."

    @pytest.mark.asyncio
    async def test_handles_llm_returning_quoted_type(self):
        config = _make_config(
            patterns=SAMPLE_PATTERNS,
            task_types=SAMPLE_TASK_TYPES,
        )
        router = MetaRouter(config=config)
        context = _make_context('"summarisation"')

        task_type, _ = await router.identify_task_type(
            "Summarise this", context,
        )

        assert task_type == "summarisation"

    @pytest.mark.asyncio
    async def test_falls_back_on_unknown_type(self):
        config = _make_config(
            patterns=SAMPLE_PATTERNS,
            task_types=SAMPLE_TASK_TYPES,
        )
        router = MetaRouter(config=config)
        context = _make_context("nonexistent-type")

        task_type, _ = await router.identify_task_type(
            "test question", context,
        )

        assert task_type == DEFAULT_TASK_TYPE

    @pytest.mark.asyncio
    async def test_falls_back_on_llm_error(self):
        config = _make_config(
            patterns=SAMPLE_PATTERNS,
            task_types=SAMPLE_TASK_TYPES,
        )
        router = MetaRouter(config=config)

        client = AsyncMock()
        client.prompt = AsyncMock(side_effect=RuntimeError("LLM down"))
        context = lambda name: client

        task_type, _ = await router.identify_task_type(
            "test question", context,
        )

        assert task_type == DEFAULT_TASK_TYPE


class TestSelectPattern:

    @pytest.mark.asyncio
    async def test_skips_llm_when_single_valid_pattern(self):
        config = _make_config(
            patterns=SAMPLE_PATTERNS,
            task_types=SAMPLE_TASK_TYPES,
        )
        router = MetaRouter(config=config)
        context = _make_context("should not be called")

        # summarisation only has ["react"]
        pattern = await router.select_pattern(
            "Summarise this", "summarisation", context,
        )

        assert pattern == "react"

    @pytest.mark.asyncio
    async def test_uses_llm_when_multiple_valid_patterns(self):
        config = _make_config(
            patterns=SAMPLE_PATTERNS,
            task_types=SAMPLE_TASK_TYPES,
        )
        router = MetaRouter(config=config)
        context = _make_context("plan-then-execute")

        # research has ["react", "plan-then-execute"]
        pattern = await router.select_pattern(
            "Research this", "research", context,
        )

        assert pattern == "plan-then-execute"

    @pytest.mark.asyncio
    async def test_respects_valid_patterns_constraint(self):
        config = _make_config(
            patterns=SAMPLE_PATTERNS,
            task_types=SAMPLE_TASK_TYPES,
        )
        router = MetaRouter(config=config)
        # LLM returns supervisor, but research doesn't allow it
        context = _make_context("supervisor")

        pattern = await router.select_pattern(
            "Research this", "research", context,
        )

        # Should fall back to first valid pattern
        assert pattern == "react"

    @pytest.mark.asyncio
    async def test_falls_back_on_llm_error(self):
        config = _make_config(
            patterns=SAMPLE_PATTERNS,
            task_types=SAMPLE_TASK_TYPES,
        )
        router = MetaRouter(config=config)

        client = AsyncMock()
        client.prompt = AsyncMock(side_effect=RuntimeError("LLM down"))
        context = lambda name: client

        # general has ["react", "plan-then-execute", "supervisor"]
        pattern = await router.select_pattern(
            "test", "general", context,
        )

        # Falls back to first valid pattern
        assert pattern == "react"

    @pytest.mark.asyncio
    async def test_falls_back_to_default_for_unknown_task_type(self):
        config = _make_config(
            patterns=SAMPLE_PATTERNS,
            task_types=SAMPLE_TASK_TYPES,
        )
        router = MetaRouter(config=config)
        context = _make_context("react")

        # Unknown task type — valid_patterns falls back to all patterns
        pattern = await router.select_pattern(
            "test", "unknown-type", context,
        )

        assert pattern == "react"


class TestRoute:

    @pytest.mark.asyncio
    async def test_full_routing_pipeline(self):
        config = _make_config(
            patterns=SAMPLE_PATTERNS,
            task_types=SAMPLE_TASK_TYPES,
        )
        router = MetaRouter(config=config)

        # Mock context where prompt returns different values per call
        client = AsyncMock()
        call_count = 0

        async def mock_prompt(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "research"  # task type
            return "plan-then-execute"  # pattern

        client.prompt = mock_prompt
        context = lambda name: client

        pattern, task_type, framing = await router.route(
            "Research the relationships", context,
        )

        assert task_type == "research"
        assert pattern == "plan-then-execute"
        assert framing == "Focus on gathering information."
