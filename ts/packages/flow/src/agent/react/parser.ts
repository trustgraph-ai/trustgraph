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

export interface StreamingReActParser {
  readonly feed: (text: string) => void;
  readonly flush: () => void;
}

export function makeStreamingReActParser(
  onThought: (text: string) => void,
  onAction: (name: string) => void,
  onActionInput: (input: string) => void,
  onFinalAnswer: (text: string) => void,
): StreamingReActParser {
  let state: ReActState = "initial";
  let buffer = "";

  const emitContent = (content: string): void => {
    if (content.length === 0) return;

    switch (state) {
      case "thought":
        onThought(content);
        break;
      case "action":
        onAction(content);
        break;
      case "action_input":
        onActionInput(content);
        break;
      case "final_answer":
        onFinalAnswer(content);
        break;
      case "initial":
        // Content before any marker -- treat as thought
        state = "thought";
        onThought(content);
        break;
      case "complete":
        break;
    }
  };

  const processLine = (line: string): void => {
    const trimmed = line.trimStart();

    // Check if this line starts a new section
    for (const marker of MARKERS) {
      if (trimmed.startsWith(marker.prefix)) {
        const content = trimmed.slice(marker.prefix.length).trim();
        state = marker.state;
        emitContent(content);
        return;
      }
    }

    // Otherwise, this is continuation content for the current state
    if (trimmed.length > 0) {
      emitContent(trimmed);
    }
  };

  const processBuffer = (isFinal: boolean): void => {
    // Process complete lines (terminated by newline)
    while (true) {
      const newlineIdx = buffer.indexOf("\n");
      if (newlineIdx === -1) {
        // No complete line yet.
        // If not final, check for partial marker match at the end and wait.
        if (!isFinal) {
          // If the remaining buffer could be the start of a marker, wait for more input.
          const trimmed = buffer.trimStart();
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

      const line = buffer.slice(0, newlineIdx);
      buffer = buffer.slice(newlineIdx + 1);
      processLine(line);
    }
  };

  /**
   * Feed a chunk of LLM output text into the parser.
   * Accumulates in a buffer and processes complete lines.
   */
  const feed = (text: string): void => {
    buffer += text;
    processBuffer(false);
  };

  const flush = (): void => {
    processBuffer(true);
    // Emit any remaining buffer content in the current state
    if (buffer.trim().length > 0) {
      emitContent(buffer);
      buffer = "";
    }
  };

  return { feed, flush };
}
