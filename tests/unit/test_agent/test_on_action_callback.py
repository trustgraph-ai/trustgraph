"""
Tests for the on_action callback in react() — verifies that it fires
after action selection but before tool execution.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from trustgraph.agent.react.agent_manager import AgentManager
from trustgraph.agent.react.types import Action, Final, Tool, Argument


class TestOnActionCallback:

    @pytest.mark.asyncio
    async def test_on_action_called_for_tool_use(self):
        """on_action fires when react() selects a tool (not Final)."""
        call_log = []

        async def fake_on_action(act):
            call_log.append(("on_action", act.name))

        # Tool that records when it's invoked
        async def tool_invoke(**kwargs):
            call_log.append(("tool_invoke",))
            return "tool result"

        tool_impl = MagicMock()
        tool_impl.return_value.invoke = AsyncMock(side_effect=tool_invoke)

        tools = {
            "search": Tool(
                name="search",
                description="Search",
                implementation=tool_impl,
                arguments=[Argument(name="query", type="string", description="q")],
                config={},
            ),
        }

        agent = AgentManager(tools=tools)

        # Mock reason() to return an Action
        action = Action(thought="thinking", name="search", arguments={"query": "test"}, observation="")
        agent.reason = AsyncMock(return_value=action)

        think = AsyncMock()
        observe = AsyncMock()
        context = MagicMock()

        await agent.react(
            question="test",
            history=[],
            think=think,
            observe=observe,
            context=context,
            on_action=fake_on_action,
        )

        # on_action should fire before tool_invoke
        assert len(call_log) == 2
        assert call_log[0] == ("on_action", "search")
        assert call_log[1] == ("tool_invoke",)

    @pytest.mark.asyncio
    async def test_on_action_not_called_for_final(self):
        """on_action does not fire when react() returns Final."""
        called = []

        async def fake_on_action(act):
            called.append(act)

        agent = AgentManager(tools={})
        agent.reason = AsyncMock(
            return_value=Final(thought="done", final="answer")
        )

        think = AsyncMock()
        observe = AsyncMock()
        context = MagicMock()

        result = await agent.react(
            question="test",
            history=[],
            think=think,
            observe=observe,
            context=context,
            on_action=fake_on_action,
        )

        assert isinstance(result, Final)
        assert len(called) == 0

    @pytest.mark.asyncio
    async def test_on_action_none_accepted(self):
        """react() works fine when on_action is None (default)."""
        async def tool_invoke(**kwargs):
            return "result"

        tool_impl = MagicMock()
        tool_impl.return_value.invoke = AsyncMock(side_effect=tool_invoke)

        tools = {
            "search": Tool(
                name="search",
                description="Search",
                implementation=tool_impl,
                arguments=[],
                config={},
            ),
        }

        agent = AgentManager(tools=tools)
        agent.reason = AsyncMock(
            return_value=Action(thought="t", name="search", arguments={}, observation="")
        )

        think = AsyncMock()
        observe = AsyncMock()
        context = MagicMock()

        result = await agent.react(
            question="test",
            history=[],
            think=think,
            observe=observe,
            context=context,
            # on_action not passed — defaults to None
        )

        assert isinstance(result, Action)
        assert result.observation == "result"
