
import logging
import json

from . types import Action, Final

logger = logging.getLogger(__name__)

class AgentManager:

    def __init__(self, tools, additional_context=None):
        self.tools = tools
        self.additional_context = additional_context

    async def reason(self, question, history, context):

        tools = self.tools

        tool_names = ",".join([
            t for t in self.tools.keys()
        ])

        variables = {
            "question": question,
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "arguments": [
                        {
                            "name": arg.name,
                            "type": arg.type,
                            "description": arg.description
                        }
                        for arg in tool.arguments.values()
                    ]
                }
                for tool in self.tools.values()
            ],
            "context": self.additional_context,
            "question": question,
            "tool_names": tool_names,
            "history": [
                {
                    "thought": h.thought,
                    "action": h.name,
                    "arguments": h.arguments,
                    "observation": h.observation,
                }
                for h in history
            ]
        }

        print(json.dumps(variables, indent=4), flush=True)

        logger.info(f"prompt: {variables}")

        obj = await context("prompt-request").agent_react(variables)

        print(json.dumps(obj, indent=4), flush=True)

        logger.info(f"response: {obj}")

        if obj.get("final-answer"):

            a = Final(
                thought = obj.get("thought"),
                final = obj.get("final-answer"),
            )

            return a

        else:

            a = Action(
                thought = obj.get("thought"),
                name = obj.get("action"),
                arguments = obj.get("arguments"),
                observation = ""
            )

            return a

    async def react(self, question, history, think, observe, context):

        act = await self.reason(
            question = question,
            history = history,
            context = context,
        )
        logger.info(f"act: {act}")

        if isinstance(act, Final):

            await think(act.thought)
            return act

        else:

            await think(act.thought)

            if act.name in self.tools:
                action = self.tools[act.name]
            else:
                raise RuntimeError(f"No action for {act.name}!")

            print("TOOL>>>", act)
            resp = await action.implementation(context).invoke(
                **act.arguments
            )

            print("RSETUL", resp)

            resp = resp.strip()

            logger.info(f"resp: {resp}")

            await observe(resp)

            act.observation = resp

            logger.info(f"iter: {act}")

            return act

