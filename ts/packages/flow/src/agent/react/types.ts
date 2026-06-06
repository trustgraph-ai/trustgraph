/**
 * Types for the ReAct agent service.
 */

import type { Effect } from "effect";
import * as S from "effect/Schema";
import { errorMessage } from "@trustgraph/base";

export class AgentToolError extends S.TaggedErrorClass<AgentToolError>()(
  "AgentToolError",
  {
    message: S.String,
    operation: S.String,
  },
) {}

export const agentToolError = (operation: string, cause: unknown): AgentToolError =>
  AgentToolError.make({
    operation,
    message: errorMessage(cause),
  });

export interface ToolArg {
  name: string;
  type: string;
  description: string;
}

export interface AgentTool {
  name: string;
  description: string;
  args: ToolArg[];
  execute: (input: string) => Effect.Effect<string, AgentToolError>;
  /** Full tool config from config-push (used by tool filtering). */
  config?: Record<string, unknown>;
}

export type ReActState =
  | "initial"
  | "thought"
  | "action"
  | "action_input"
  | "final_answer"
  | "complete";

export interface ParsedEvent {
  type: "thought" | "action" | "action_input" | "final_answer";
  content: string;
}

export type OnThought = (text: string, isFinal: boolean) => Effect.Effect<void, AgentToolError>;
export type OnObservation = (text: string, isFinal: boolean) => Effect.Effect<void, AgentToolError>;
export type OnAnswer = (text: string) => Effect.Effect<void, AgentToolError>;
