/**
 * Types for the ReAct agent service.
 */

export interface ToolArg {
  name: string;
  type: string;
  description: string;
}

export interface AgentTool {
  name: string;
  description: string;
  args: ToolArg[];
  execute: (input: string) => Promise<string>;
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

export type OnThought = (text: string, isFinal: boolean) => Promise<void>;
export type OnObservation = (text: string, isFinal: boolean) => Promise<void>;
export type OnAnswer = (text: string) => Promise<void>;
