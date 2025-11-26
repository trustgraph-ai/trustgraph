"""
Streaming parser for ReAct responses.

This parser handles text chunks from LLM streaming responses and parses them
into ReAct format (Thought/Action/Args or Thought/Final Answer). It maintains
state across chunk boundaries to handle cases where delimiters or JSON are split.

Key challenges:
- Delimiters may be split across chunks: "Tho" + "ught:" or "Final An" + "swer:"
- JSON arguments may be split: '{"loc' + 'ation": "NYC"}'
- Need to emit thought/answer chunks as they arrive for streaming
"""

import json
import logging
import re
from enum import Enum
from typing import Optional, Callable, Any
from . types import Action, Final

logger = logging.getLogger(__name__)


class ParserState(Enum):
    """States for the streaming ReAct parser state machine"""
    INITIAL = "initial"              # Waiting for first content
    THOUGHT = "thought"              # Accumulating thought content
    ACTION = "action"                # Found "Action:", collecting action name
    ARGS = "args"                    # Found "Args:", collecting JSON arguments
    FINAL_ANSWER = "final_answer"    # Found "Final Answer:", collecting answer
    COMPLETE = "complete"            # Parsing complete, object ready


class StreamingReActParser:
    """
    Stateful parser for streaming ReAct responses.

    Expected format:
        Thought: [reasoning about what to do next]
        Action: [tool_name]
        Args: {
            "param": "value"
        }

    OR
        Thought: [reasoning about the final answer]
        Final Answer: [the answer]

    Usage:
        parser = StreamingReActParser(
            on_thought_chunk=lambda chunk: print(f"Thought: {chunk}"),
            on_answer_chunk=lambda chunk: print(f"Answer: {chunk}"),
        )

        for chunk in llm_stream:
            parser.feed(chunk)
            if parser.is_complete():
                result = parser.get_result()
                break
    """

    # Delimiters we're looking for
    THOUGHT_DELIMITER = "Thought:"
    ACTION_DELIMITER = "Action:"
    ARGS_DELIMITER = "Args:"
    FINAL_ANSWER_DELIMITER = "Final Answer:"

    # Maximum buffer size for delimiter detection (longest delimiter + safety margin)
    MAX_DELIMITER_BUFFER = 20

    def __init__(
        self,
        on_thought_chunk: Optional[Callable[[str], Any]] = None,
        on_answer_chunk: Optional[Callable[[str], Any]] = None,
    ):
        """
        Initialize streaming parser.

        Args:
            on_thought_chunk: Callback for thought text chunks as they arrive
            on_answer_chunk: Callback for final answer text chunks as they arrive
        """
        self.on_thought_chunk = on_thought_chunk
        self.on_answer_chunk = on_answer_chunk

        # Parser state
        self.state = ParserState.INITIAL

        # Buffers for accumulating content
        self.line_buffer = ""           # For detecting delimiters across chunk boundaries
        self.thought_buffer = ""        # Accumulated thought text
        self.action_buffer = ""         # Action name
        self.args_buffer = ""           # JSON arguments text
        self.answer_buffer = ""         # Final answer text

        # JSON parsing state for Args
        self.brace_count = 0
        self.args_started = False

        # Result object (Action or Final)
        self.result = None

    def feed(self, chunk: str) -> None:
        """
        Feed a text chunk to the parser.

        Args:
            chunk: Text chunk from LLM stream
        """
        if self.state == ParserState.COMPLETE:
            return  # Already complete, ignore further chunks

        # Add chunk to line buffer for delimiter detection
        self.line_buffer += chunk

        # Remove markdown code blocks if present
        self.line_buffer = re.sub(r'^```[^\n]*\n', '', self.line_buffer)
        self.line_buffer = re.sub(r'\n```$', '', self.line_buffer)

        # Process based on current state
        # Track previous state to detect if we're making progress
        while self.line_buffer and self.state != ParserState.COMPLETE:
            prev_buffer_len = len(self.line_buffer)
            prev_state = self.state

            if self.state == ParserState.INITIAL:
                self._process_initial()
            elif self.state == ParserState.THOUGHT:
                self._process_thought()
            elif self.state == ParserState.ACTION:
                self._process_action()
            elif self.state == ParserState.ARGS:
                self._process_args()
            elif self.state == ParserState.FINAL_ANSWER:
                self._process_final_answer()

            # If no progress was made (buffer unchanged AND state unchanged), break
            # to avoid infinite loop. We'll process more when the next chunk arrives.
            if len(self.line_buffer) == prev_buffer_len and self.state == prev_state:
                break

    def _process_initial(self) -> None:
        """Process INITIAL state - looking for 'Thought:' delimiter"""
        idx = self.line_buffer.find(self.THOUGHT_DELIMITER)

        if idx >= 0:
            # Found thought delimiter
            # Discard any content before it and strip leading whitespace after delimiter
            self.line_buffer = self.line_buffer[idx + len(self.THOUGHT_DELIMITER):].lstrip()
            self.state = ParserState.THOUGHT
        elif len(self.line_buffer) >= self.MAX_DELIMITER_BUFFER:
            # Buffer getting too large, probably junk before thought
            # Keep only the tail that might contain partial delimiter
            self.line_buffer = self.line_buffer[-self.MAX_DELIMITER_BUFFER:]

    def _process_thought(self) -> None:
        """Process THOUGHT state - accumulating thought content"""
        # Check for Action or Final Answer delimiter
        action_idx = self.line_buffer.find(self.ACTION_DELIMITER)
        final_idx = self.line_buffer.find(self.FINAL_ANSWER_DELIMITER)

        # Find which delimiter comes first (if any)
        next_delimiter_idx = -1
        next_state = None

        if action_idx >= 0 and (final_idx < 0 or action_idx < final_idx):
            next_delimiter_idx = action_idx
            next_state = ParserState.ACTION
            delimiter_len = len(self.ACTION_DELIMITER)
        elif final_idx >= 0:
            next_delimiter_idx = final_idx
            next_state = ParserState.FINAL_ANSWER
            delimiter_len = len(self.FINAL_ANSWER_DELIMITER)

        if next_delimiter_idx >= 0:
            # Found next delimiter
            thought_chunk = self.line_buffer[:next_delimiter_idx].strip()
            if thought_chunk:
                self.thought_buffer += thought_chunk
                if self.on_thought_chunk:
                    self.on_thought_chunk(thought_chunk)

            self.line_buffer = self.line_buffer[next_delimiter_idx + delimiter_len:].lstrip()
            self.state = next_state
        else:
            # No delimiter found yet
            # Keep tail in buffer (might contain partial delimiter)
            # Emit the rest as thought chunk
            if len(self.line_buffer) > self.MAX_DELIMITER_BUFFER:
                emittable = self.line_buffer[:-self.MAX_DELIMITER_BUFFER]
                self.thought_buffer += emittable
                if self.on_thought_chunk:
                    self.on_thought_chunk(emittable)
                self.line_buffer = self.line_buffer[-self.MAX_DELIMITER_BUFFER:]

    def _process_action(self) -> None:
        """Process ACTION state - collecting action name"""
        # Action name is on one line (or at least until newline or Args:)
        newline_idx = self.line_buffer.find('\n')
        args_idx = self.line_buffer.find(self.ARGS_DELIMITER)

        # Find which comes first
        if args_idx >= 0 and (newline_idx < 0 or args_idx < newline_idx):
            # Args delimiter found first
            # Only set action_buffer if not already set (to avoid overwriting with empty string)
            if not self.action_buffer:
                self.action_buffer = self.line_buffer[:args_idx].strip().strip('"')
            self.line_buffer = self.line_buffer[args_idx + len(self.ARGS_DELIMITER):].lstrip()
            self.state = ParserState.ARGS
        elif newline_idx >= 0:
            # Newline found, action name complete
            # Only set action_buffer if not already set
            if not self.action_buffer:
                self.action_buffer = self.line_buffer[:newline_idx].strip().strip('"')
            self.line_buffer = self.line_buffer[newline_idx + 1:]
            # Stay in ACTION state or move to ARGS if we find delimiter
            # Actually, check if next line has Args:
            if self.line_buffer.lstrip().startswith(self.ARGS_DELIMITER):
                args_start = self.line_buffer.find(self.ARGS_DELIMITER)
                self.line_buffer = self.line_buffer[args_start + len(self.ARGS_DELIMITER):].lstrip()
                self.state = ParserState.ARGS
        else:
            # Not enough content yet, keep buffering
            # But if buffer is getting large, action name is probably complete
            if len(self.line_buffer) > 100:
                self.action_buffer = self.line_buffer.strip().strip('"')
                self.line_buffer = ""
                # Assume Args comes next, but we need more content
                self.state = ParserState.ARGS

    def _process_args(self) -> None:
        """Process ARGS state - collecting JSON arguments"""
        # Process character by character to track brace matching
        i = 0
        while i < len(self.line_buffer):
            char = self.line_buffer[i]
            self.args_buffer += char

            if char == '{':
                self.brace_count += 1
                self.args_started = True
            elif char == '}':
                self.brace_count -= 1

            # Check if JSON is complete
            if self.args_started and self.brace_count == 0:
                # JSON complete, try to parse
                try:
                    args_dict = json.loads(self.args_buffer.strip())
                    # Success! Create Action result
                    self.result = Action(
                        thought=self.thought_buffer.strip(),
                        name=self.action_buffer,
                        arguments=args_dict,
                        observation=""
                    )
                    self.state = ParserState.COMPLETE
                    self.line_buffer = ""  # Clear buffer
                    return
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON args: {self.args_buffer}")
                    raise ValueError(f"Invalid JSON in Args: {e}")

            i += 1

        # Consumed entire buffer, clear it and wait for more chunks
        self.line_buffer = ""

    def _process_final_answer(self) -> None:
        """Process FINAL_ANSWER state - collecting final answer"""
        # For final answer, we consume everything until we decide we're done
        # In streaming mode, we can't know when answer is complete until stream ends
        # So we emit chunks and accumulate

        # Check if this might be JSON
        is_json = self.answer_buffer.strip().startswith('{') or \
                  self.line_buffer.strip().startswith('{')

        if is_json:
            # Handle JSON final answer
            self.answer_buffer += self.line_buffer

            # Count braces to detect completion
            brace_count = self.answer_buffer.count('{') - self.answer_buffer.count('}')

            if brace_count == 0 and '{' in self.answer_buffer:
                # JSON might be complete
                # Note: We can't be 100% sure without trying to parse
                # But in streaming mode, we'll finish when stream ends
                pass

            # Emit chunk
            if self.on_answer_chunk:
                self.on_answer_chunk(self.line_buffer)

            self.line_buffer = ""
        else:
            # Regular text answer - emit everything
            if self.line_buffer:
                self.answer_buffer += self.line_buffer
                if self.on_answer_chunk:
                    self.on_answer_chunk(self.line_buffer)
                self.line_buffer = ""

    def finalize(self) -> None:
        """
        Call this when the stream is complete to finalize parsing.
        This handles any remaining buffered content.
        """
        if self.state == ParserState.COMPLETE:
            return

        # Flush any remaining thought chunks
        if self.state == ParserState.THOUGHT and self.line_buffer:
            self.thought_buffer += self.line_buffer
            if self.on_thought_chunk:
                self.on_thought_chunk(self.line_buffer)
            self.line_buffer = ""

        # Finalize final answer
        if self.state == ParserState.FINAL_ANSWER:
            # Flush any remaining answer content
            if self.line_buffer:
                self.answer_buffer += self.line_buffer
                if self.on_answer_chunk:
                    self.on_answer_chunk(self.line_buffer)
                self.line_buffer = ""

            # Create Final result
            self.result = Final(
                thought=self.thought_buffer.strip(),
                final=self.answer_buffer.strip()
            )
            self.state = ParserState.COMPLETE

        # If we're in other states, something went wrong
        if self.state not in [ParserState.COMPLETE, ParserState.FINAL_ANSWER]:
            if self.thought_buffer:
                raise ValueError(
                    f"Stream ended in {self.state.value} state with incomplete parsing. "
                    f"Thought: {self.thought_buffer[:100]}..."
                )
            else:
                raise ValueError(f"Stream ended in {self.state.value} state with no content")

    def is_complete(self) -> bool:
        """Check if parsing is complete"""
        return self.state == ParserState.COMPLETE

    def get_result(self) -> Optional[Action | Final]:
        """Get the parsed result (Action or Final)"""
        return self.result
