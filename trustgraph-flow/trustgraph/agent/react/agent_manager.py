
import ibis
import logging
import json

from . types import Action, Final

logger = logging.getLogger(__name__)

class AgentManager:

    template="""Answer the following questions as best you can. You have
access to the following functions:

{% for tool in tools %}{
    "function": "{{ tool.name }}",
    "description": "{{ tool.description }}",
    "arguments": [
{% for arg in tool.arguments %}        {
            "name": "{{ arg.name }}",
            "type": "{{ arg.type }}",
            "description": "{{ arg.description }}",
        }
{% endfor %}
    ]
}
{% endfor %}

You can either choose to call a function to get more information, or
return a final answer.
    
To call a function, respond with a JSON object of the following format:

{
    "thought": "your thought about what to do",
    "action": "the action to take, should be one of [{{tool_names}}]",
    "arguments": {
        "argument1": "argument_value",
        "argument2": "argument_value"
    }
}

To provide a final answer, response a JSON object of the following format:

{
  "thought": "I now know the final answer",
  "final-answer": "the final answer to the original input question"
}

Previous steps are included in the input.  Each step has the following
format in your output:

{
  "thought": "your thought about what to do",
  "action": "the action taken",
  "arguments": {
      "argument1": action argument,
      "argument2": action argument2
  },
  "observation": "the result of the action",
}

Respond by describing either one single thought/action/arguments or
the final-answer.  Pause after providing one action or final-answer.

{% if context %}Additional context has been provided:
{{context}}{% endif %}

Question: {{question}}

Input:
    
{% for h in history %}
{
    "action": "{{h.action}}",
    "arguments": [
{% for k, v in h.arguments.items() %}        {
            "{{k}}": "{{v}}",
{%endfor%}        }
    ],
    "observation": "{{h.observation}}"
}
{% endfor %}"""

    def __init__(self, context, tools, additional_context=None):
        self.context = context
        self.tools = tools
        self.additional_context = additional_context

    def reason(self, question, history):

        tpl = ibis.Template(self.template)

        tools = self.tools

        tool_names = ",".join([
            t for t in self.tools.keys()
        ])

        prompt = tpl.render({
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
            ],
        })

        print(prompt)

        logger.info(f"prompt: {prompt}")

        resp = self.context.prompt.request(
            "question",
            {
                "question": prompt
            }
        )

        resp = resp.replace("```json", "")
        resp = resp.replace("```", "")

        logger.info(f"response: {resp}")

        obj = json.loads(resp)

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

    def react(self, question, history, think, observe):

        act = self.reason(question, history)
        logger.info(f"act: {act}")

        if isinstance(act, Final):

            think(act.thought)
            return act

        else:

            think(act.thought)

            if act.name in self.tools:
                action = self.tools[act.name]
            else:
                raise RuntimeError(f"No action for {act.name}!")

            resp = action.implementation.invoke(**act.arguments)

            resp = resp.strip()

            logger.info(f"resp: {resp}")

            observe(resp)

            act.observation = resp

            logger.info(f"iter: {act}")

            return act

