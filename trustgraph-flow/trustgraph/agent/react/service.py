"""
Simple agent infrastructure broadly implements the ReAct flow.
"""

import json
import re
import sys

from pulsar.schema import JsonSchema

from ... base import ConsumerProducer
from ... schema import Error
from ... schema import AgentRequest, AgentResponse, AgentStep
from ... schema import agent_request_queue, agent_response_queue
from ... schema import prompt_request_queue as pr_request_queue
from ... schema import prompt_response_queue as pr_response_queue
from ... schema import text_completion_request_queue as tc_request_queue
from ... schema import text_completion_response_queue as tc_response_queue
from ... schema import graph_rag_request_queue as gr_request_queue
from ... schema import graph_rag_response_queue as gr_response_queue
from ... clients.prompt_client import PromptClient
from ... clients.llm_client import LlmClient
from ... clients.graph_rag_client import GraphRagClient

from . tools import KnowledgeQueryImpl, TextCompletionImpl
from . agent_manager import AgentManager

from . types import Final, Action, Tool, Argument

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = agent_request_queue
default_output_queue = agent_response_queue
default_subscriber = module
default_max_iterations = 15

class Processor(ConsumerProducer):

    def __init__(self, **params):

        additional = params.get("context", None)

        self.max_iterations = int(params.get("max_iterations", default_max_iterations))

        tools = {}

        # Parsing the prompt information to the prompt configuration
        # structure
        tool_type_arg = params.get("tool_type", [])
        if tool_type_arg:
            for t in tool_type_arg:
                toks = t.split("=", 1)
                if len(toks) < 2:
                    raise RuntimeError(
                        f"Tool-type string not well-formed: {t}"
                    )
                ttoks = toks[1].split(":", 1)
                if len(ttoks) < 1:
                    raise RuntimeError(
                        f"Tool-type string not well-formed: {t}"
                    )

                if ttoks[0] == "knowledge-query":
                    impl = KnowledgeQueryImpl(self)
                elif ttoks[0] == "text-completion":
                    impl = TextCompletionImpl(self)
                else:
                    raise RuntimeError(
                        f"Tool-kind {ttoks[0]} not known"
                    )

                if len(ttoks) == 1:

                    tools[toks[0]] = Tool(
                        name = toks[0],
                        description = "",
                        implementation = impl,
                        config = { "input": "query" },
                        arguments = {},
                    )
                else:
                    tools[toks[0]] = Tool(
                        name = toks[0],
                        description = "",
                        implementation = impl,
                        config = { "input": ttoks[1] },
                        arguments = {},
                    )

        # parsing the prompt information to the prompt configuration
        # structure
        tool_desc_arg = params.get("tool_description", [])
        if tool_desc_arg:
            for t in tool_desc_arg:
                toks = t.split("=", 1)
                if len(toks) < 2:
                    raise runtimeerror(
                        f"tool-type string not well-formed: {t}"
                    )
                if toks[0] not in tools:
                    raise runtimeerror(f"description, tool {toks[0]} not known")
                tools[toks[0]].description = toks[1]

        # Parsing the prompt information to the prompt configuration
        # structure
        tool_arg_arg = params.get("tool_argument", [])
        if tool_arg_arg:
            for t in tool_arg_arg:
                toks = t.split("=", 1)
                if len(toks) < 2:
                    raise RuntimeError(
                        f"Tool-type string not well-formed: {t}"
                    )
                ttoks = toks[1].split(":", 2)
                if len(ttoks) != 3:
                    raise RuntimeError(
                        f"Tool argument string not well-formed: {t}"
                    )
                if toks[0] not in tools:
                    raise RuntimeError(f"Description, tool {toks[0]} not known")
                tools[toks[0]].arguments[ttoks[0]] = Argument(
                    name = ttoks[0],
                    type = ttoks[1],
                    description = ttoks[2]
                )

        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)
        prompt_request_queue = params.get(
            "prompt_request_queue", pr_request_queue
        )
        prompt_response_queue = params.get(
            "prompt_response_queue", pr_response_queue
        )
        text_completion_request_queue = params.get(
            "text_completion_request_queue", tc_request_queue
        )
        text_completion_response_queue = params.get(
            "text_completion_response_queue", tc_response_queue
        )
        graph_rag_request_queue = params.get(
            "graph_rag_request_queue", gr_request_queue
        )
        graph_rag_response_queue = params.get(
            "graph_rag_response_queue", gr_response_queue
        )

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "output_queue": output_queue,
                "subscriber": subscriber,
                "input_schema": AgentRequest,
                "output_schema": AgentResponse,
                "prompt_request_queue": prompt_request_queue,
                "prompt_response_queue": prompt_response_queue,
                "text_completion_request_queue": tc_request_queue,
                "text_completion_response_queue": tc_response_queue,
                "graph_rag_request_queue": gr_request_queue,
                "graph_rag_response_queue": gr_response_queue,
            }
        )

        self.prompt = PromptClient(
            subscriber=subscriber,
            input_queue=prompt_request_queue,
            output_queue=prompt_response_queue,
            pulsar_host = self.pulsar_host,
            pulsar_api_key=self.pulsar_api_key,
        )

        self.llm = LlmClient(
            subscriber=subscriber,
            input_queue=text_completion_request_queue,
            output_queue=text_completion_response_queue,
            pulsar_host = self.pulsar_host,
            pulsar_api_key=self.pulsar_api_key,
        )

        self.graph_rag = GraphRagClient(
            subscriber=subscriber,
            input_queue=graph_rag_request_queue,
            output_queue=graph_rag_response_queue,
            pulsar_host = self.pulsar_host,
            pulsar_api_key=self.pulsar_api_key,
        )

        # Need to be able to feed requests to myself
        self.recursive_input = self.client.create_producer(
            topic=input_queue,
            schema=JsonSchema(AgentRequest),
        )

        self.agent = AgentManager(
            context=self,
            tools=tools,
            additional_context=additional
        )

    def parse_json(self, text):
        json_match = re.search(r'```(?:json)?(.*?)```', text, re.DOTALL)
    
        if json_match:
            json_str = json_match.group(1).strip()
        else:
            # If no delimiters, assume the entire output is JSON
            json_str = text.strip()

        return json.loads(json_str)

    def handle(self, msg):

        try:

            v = msg.value()

            # Sender-produced ID
            id = msg.properties()["id"]

            if v.history:
                history = [
                    Action(
                        thought=h.thought,
                        name=h.action,
                        arguments=h.arguments,
                        observation=h.observation
                    )
                    for h in v.history
                ]
            else:
                history = []

            print(f"Question: {v.question}", flush=True)

            if len(history) >= self.max_iterations:
                raise RuntimeError("Too many agent iterations")

            print(f"History: {history}", flush=True)

            def think(x):

                print(f"Think: {x}", flush=True)

                r = AgentResponse(
                    answer=None,
                    error=None,
                    thought=x,
                    observation=None,
                )

                self.producer.send(r, properties={"id": id})

            def observe(x):

                print(f"Observe: {x}", flush=True)

                r = AgentResponse(
                    answer=None,
                    error=None,
                    thought=None,
                    observation=x,
                )

                self.producer.send(r, properties={"id": id})

            act = self.agent.react(v.question, history, think, observe)

            print(f"Action: {act}", flush=True)

            print("Send response...", flush=True)

            if type(act) == Final:

                r = AgentResponse(
                    answer=act.final,
                    error=None,
                    thought=None,
                )

                self.producer.send(r, properties={"id": id})

                print("Done.", flush=True)

                return

            history.append(act)

            r = AgentRequest(
                question=v.question,
                plan=v.plan,
                state=v.state,
                history=[
                    AgentStep(
                        thought=h.thought,
                        action=h.name,
                        arguments=h.arguments,
                        observation=h.observation
                    )
                    for h in history
                ]
            )

            self.recursive_input.send(r, properties={"id": id})

            print("Done.", flush=True)

            return

        except Exception as e:

            print(f"Exception: {e}")

            print("Send error response...", flush=True)

            r = AgentResponse(
                error=Error(
                    type = "agent-error",
                    message = str(e),
                ),
                response=None,
            )

            self.producer.send(r, properties={"id": id})

    @staticmethod
    def add_args(parser):

        ConsumerProducer.add_args(
            parser, default_input_queue, default_subscriber,
            default_output_queue,
        )

        parser.add_argument(
            '--prompt-request-queue',
            default=pr_request_queue,
            help=f'Prompt request queue (default: {pr_request_queue})',
        )

        parser.add_argument(
            '--prompt-response-queue',
            default=pr_response_queue,
            help=f'Prompt response queue (default: {pr_response_queue})',
        )

        parser.add_argument(
            '--text-completion-request-queue',
            default=tc_request_queue,
            help=f'Text completion request queue (default: {tc_request_queue})',
        )

        parser.add_argument(
            '--text-completion-response-queue',
            default=tc_response_queue,
            help=f'Text completion response queue (default: {tc_response_queue})',
        )

        parser.add_argument(
            '--graph-rag-request-queue',
            default=gr_request_queue,
            help=f'Graph RAG request queue (default: {gr_request_queue})',
        )

        parser.add_argument(
            '--graph-rag-response-queue',
            default=gr_response_queue,
            help=f'Graph RAG response queue (default: {gr_response_queue})',
        )

        parser.add_argument(
            '--tool-type', nargs='*',
            help=f'''Specifies the type of an agent tool.  Takes the form
<id>=<specifier>.  <id> is the name of the tool.  <specifier> is one of
knowledge-query, text-completion.  Additional parameters are specified
for different tools which are tool-specific. e.g. knowledge-query:<arg>
which specifies the name of the arg whose content is fed into the knowledge
query as a question.  text-completion:<arg> specifies the name of the arg
whose content is fed into the text-completion service as a prompt'''
        )

        parser.add_argument(
            '--tool-description', nargs='*',
            help=f'''Specifies the textual description of a tool.  Takes
the form <id>=<description>.  The description is important, it teaches the
LLM how to use the tool.  It should describe what it does and how to
use the arguments.  This is specified in natural language.'''
        )

        parser.add_argument(
            '--tool-argument', nargs='*',
            help=f'''Specifies argument usage for a tool.  Takes
the form <id>=<arg>:<type>:<description>.  The description is important,
it is read by the LLM and used to determine how to use the argument.
<id> can be specified multiple times to give a tool multiple arguments.
<type> is one of string, number.  <description> is a natural language
description.'''
        )

        parser.add_argument(
            '--context', 
            help=f'Optional, specifies additional context text for the LLM.'
        )

        parser.add_argument(
            '--max-iterations',
            default=default_max_iterations,
            help=f'Maximum number of react iterations (default: {default_max_iterations})',
        )

def run():

    Processor.start(module, __doc__)

