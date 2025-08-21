
import logging
import json
import re

from . types import Action, Final

logger = logging.getLogger(__name__)

class AgentManager:

    def __init__(self, tools, additional_context=None):
        self.tools = tools
        self.additional_context = additional_context

    def parse_react_response(self, text):
        """Parse text-based ReAct response format.
        
        Expected format:
        Thought: [reasoning about what to do next]
        Action: [tool_name]
        Args: {
            "param": "value"
        }
        
        OR
        
        Thought: [reasoning about the final answer]
        Final Answer: [the answer]
        """
        if not isinstance(text, str):
            raise ValueError(f"Expected string response, got {type(text)}")
        
        # Remove any markdown code blocks that might wrap the response
        text = re.sub(r'^```[^\n]*\n', '', text.strip())
        text = re.sub(r'\n```$', '', text.strip())
            
        lines = text.strip().split('\n')
        
        thought = None
        action = None
        args = None
        final_answer = None
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Parse Thought
            if line.startswith("Thought:"):
                thought = line[8:].strip()
                # Handle multi-line thoughts
                i += 1
                while i < len(lines):
                    next_line = lines[i].strip()
                    if next_line.startswith(("Action:", "Final Answer:", "Args:")):
                        break
                    thought += " " + next_line
                    i += 1
                continue
            
            # Parse Final Answer
            if line.startswith("Final Answer:"):
                final_answer = line[13:].strip()
                # Handle multi-line final answers (including JSON)
                i += 1
                
                # Check if the answer might be JSON
                if final_answer.startswith('{') or (i < len(lines) and lines[i].strip().startswith('{')):
                    # Collect potential JSON answer
                    json_text = final_answer if final_answer.startswith('{') else ""
                    brace_count = json_text.count('{') - json_text.count('}')
                    
                    while i < len(lines) and (brace_count > 0 or not json_text):
                        current_line = lines[i].strip()
                        if current_line.startswith(("Thought:", "Action:")) and brace_count == 0:
                            break
                        json_text += ("\n" if json_text else "") + current_line
                        brace_count += current_line.count('{') - current_line.count('}')
                        i += 1
                    
                    # Try to parse as JSON
                    # try:
                    #     final_answer = json.loads(json_text)
                    # except json.JSONDecodeError:
                    #     # Not valid JSON, treat as regular text
                    #     final_answer = json_text
                    final_answer = json_text
                else:
                    # Regular text answer
                    while i < len(lines):
                        next_line = lines[i].strip()
                        if next_line.startswith(("Thought:", "Action:")):
                            break
                        final_answer += " " + next_line
                        i += 1
                    
                # If we have a final answer, return Final object
                return Final(
                    thought=thought or "",
                    final=final_answer
                )
            
            # Parse Action
            if line.startswith("Action:"):
                action = line[7:].strip()

                # Get rid of quotation prefix/suffix if present
                while action[0] == '"':
                    action = action[1:]

                while action[-1] == '"':
                    action = action[:-1]
            
            # Parse Args
            if line.startswith("Args:"):
                # Check if JSON starts on the same line
                args_on_same_line = line[5:].strip()
                if args_on_same_line:
                    args_text = args_on_same_line
                    brace_count = args_on_same_line.count('{') - args_on_same_line.count('}')
                else:
                    args_text = ""
                    brace_count = 0
                
                # Collect all lines that form the JSON arguments
                i += 1
                started = bool(args_on_same_line and '{' in args_on_same_line)
                
                while i < len(lines) and (not started or brace_count > 0):
                    current_line = lines[i]
                    args_text += ("\n" if args_text else "") + current_line
                    
                    # Count braces to determine when JSON is complete
                    for char in current_line:
                        if char == '{':
                            brace_count += 1
                            started = True
                        elif char == '}':
                            brace_count -= 1
                    
                    # If we've started and braces are balanced, we're done
                    if started and brace_count == 0:
                        break
                    
                    i += 1
                
                # Parse the JSON arguments
                try:
                    args = json.loads(args_text.strip())
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON arguments: {args_text}")
                    raise ValueError(f"Invalid JSON in Args: {e}")
            
            i += 1
        
        # If we have an action, return Action object
        if action:
            return Action(
                thought=thought or "",
                name=action,
                arguments=args or {},
                observation=""
            )
        
        # If we only have a thought but no action or final answer
        if thought and not action and not final_answer:
            raise ValueError(f"Response has thought but no action or final answer: {text}")
        
        raise ValueError(f"Could not parse response: {text}")

    async def reason(self, question, history, context):

        logger.debug(f"calling reason: {question}")

        tools = self.tools

        logger.debug("in reason")
        logger.debug(f"tools: {tools}")

        tool_names = ",".join([
            t for t in self.tools.keys()
        ])

        logger.debug(f"Tool names: {tool_names}")

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
                        for arg in tool.arguments
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

        logger.debug(f"Variables: {json.dumps(variables, indent=4)}")

        logger.info(f"prompt: {variables}")

        # Get text response from prompt service
        response_text = await context("prompt-request").agent_react(variables)

        logger.debug(f"Response text:\n{response_text}")

        logger.info(f"response: {response_text}")

        # Parse the text response
        try:
            result = self.parse_react_response(response_text)
            logger.info(f"Parsed result: {result}")
            return result
        except ValueError as e:
            logger.error(f"Failed to parse response: {e}")
            # Try to provide a helpful error message
            logger.error(f"Response was: {response_text}")
            raise RuntimeError(f"Failed to parse agent response: {e}")

    async def react(self, question, history, think, observe, context):

        logger.info(f"question: {question}")

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

            logger.debug(f"ACTION: {act.name}")

            logger.debug(f"Tools: {self.tools.keys()}")

            if act.name in self.tools:
                action = self.tools[act.name]
            else:
                logger.debug(f"Tools: {self.tools}")
                raise RuntimeError(f"No action for {act.name}!")

            logger.debug(f"TOOL>>> {act}")

            resp = await action.implementation(context).invoke(
                **act.arguments
            )

            if isinstance(resp, str):
                resp = resp.strip()
            else:
                resp = str(resp)
                resp = resp.strip()

            logger.info(f"resp: {resp}")

            await observe(resp)

            act.observation = resp

            logger.info(f"iter: {act}")

            return act

