/**
 * Streaming ReAct parser -- state machine that processes LLM output one chunk at a time.
 *
 * Detects these markers in the LLM output:
 * - "Thought:" -> emit thought content
 * - "Action:" -> emit action name (tool name)
 * - "Action Input:" -> emit action input (JSON args)
 * - "Final Answer:" -> emit final answer content
 *
 * Handles markers split across chunks by buffering lines.
 */

import type { ReActState } from "./types.js";

const MARKERS = [
  { prefix: "Thought:", state: "thought" as ReActState },
  { prefix: "Action Input:", state: "action_input" as ReActState },
  { prefix: "Action:", state: "action" as ReActState },
  { prefix: "Final Answer:", state: "final_answer" as ReActState },
];

// Longest marker prefix for partial-match detection
const MAX_MARKER_LEN = Math.max(...MARKERS.map((m) => m.prefix.length));

export class StreamingReActParser {
  private state: ReActState = "initial";
  private buffer = "";
  private onThought: (text: string) => void;
  private onAction: (name: string) => void;
  private onActionInput: (input: string) => void;
  private onFinalAnswer: (text: string) => void;

  constructor(
    onThought: (text: string) => void,
    onAction: (name: string) => void,
    onActionInput: (input: string) => void,
    onFinalAnswer: (text: string) => void,
  ) {
    this.onThought = onThought;
    this.onAction = onAction;
    this.onActionInput = onActionInput;
    this.onFinalAnswer = onFinalAnswer;
  }

  /**
   * Feed a chunk of LLM output text into the parser.
   * Accumulates in a buffer and processes complete lines.
   */
  feed(text: string): void {
    this.buffer += text;
    this.processBuffer(false);
  }

  /**
   * Flush any remaining buffered content at the end of output.
   */
  flush(): void {
    this.processBuffer(true);
    // Emit any remaining buffer content in the current state
    if (this.buffer.trim().length > 0) {
      this.emitContent(this.buffer);
      this.buffer = "";
    }
  }

  private processBuffer(isFinal: boolean): void {
    // Process complete lines (terminated by newline)
    while (true) {
      const newlineIdx = this.buffer.indexOf("\n");
      if (newlineIdx === -1) {
        // No complete line yet.
        // If not final, check for partial marker match at the end and wait.
        if (!isFinal) {
          // If the remaining buffer could be the start of a marker, wait for more input.
          const trimmed = this.buffer.trimStart();
          if (trimmed.length > 0 && trimmed.length < MAX_MARKER_LEN) {
            const couldBeMarker = MARKERS.some((m) =>
              m.prefix.startsWith(trimmed),
            );
            if (couldBeMarker) {
              // Wait for more input before deciding
              return;
            }
          }
        }
        break;
      }

      const line = this.buffer.slice(0, newlineIdx);
      this.buffer = this.buffer.slice(newlineIdx + 1);
      this.processLine(line);
    }
  }

  private processLine(line: string): void {
    const trimmed = line.trimStart();

    // Check if this line starts a new section
    for (const marker of MARKERS) {
      if (trimmed.startsWith(marker.prefix)) {
        const content = trimmed.slice(marker.prefix.length).trim();
        this.state = marker.state;
        this.emitContent(content);
        return;
      }
    }

    // Otherwise, this is continuation content for the current state
    if (trimmed.length > 0) {
      this.emitContent(trimmed);
    }
  }

  private emitContent(content: string): void {
    if (content.length === 0) return;

    switch (this.state) {
      case "thought":
        this.onThought(content);
        break;
      case "action":
        this.onAction(content);
        break;
      case "action_input":
        this.onActionInput(content);
        break;
      case "final_answer":
        this.onFinalAnswer(content);
        break;
      case "initial":
        // Content before any marker -- treat as thought
        this.state = "thought";
        this.onThought(content);
        break;
      case "complete":
        break;
    }
  }
}
