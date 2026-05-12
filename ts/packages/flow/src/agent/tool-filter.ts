/**
 * Tool filtering logic for the TrustGraph tool group system.
 *
 * Filters available tools based on group membership and execution state.
 *
 * Python reference: trustgraph-flow/trustgraph/agent/tool_filter.py
 */

import type { AgentTool } from "./react/types.js";

/**
 * Filter tools based on group membership and execution state.
 */
export function filterToolsByGroupAndState(
  tools: AgentTool[],
  requestedGroups?: string[],
  currentState?: string,
): AgentTool[] {
  const groups = requestedGroups ?? ["default"];
  const state = currentState ?? "undefined";

  return tools.filter((tool) => isToolAvailable(tool, groups, state));
}

function isToolAvailable(
  tool: AgentTool,
  requestedGroups: string[],
  currentState: string,
): boolean {
  const config = tool.config ?? {};

  // Get tool groups (default to ["default"])
  let toolGroups = config["group"] as string[] | string | undefined;
  if (toolGroups === undefined) toolGroups = ["default"];
  if (!Array.isArray(toolGroups)) toolGroups = [toolGroups];

  // Get tool applicable states (default to ["*"] = all states)
  let applicableStates = config["applicable-states"] as string[] | string | undefined;
  if (applicableStates === undefined) applicableStates = ["*"];
  if (!Array.isArray(applicableStates)) applicableStates = [applicableStates];

  // Group match: wildcard in requested groups, or intersection non-empty
  const groupMatch =
    requestedGroups.includes("*") ||
    toolGroups.some((g) => requestedGroups.includes(g));

  // State match: wildcard in applicable states, or current state matches
  const stateMatch =
    applicableStates.includes("*") ||
    applicableStates.includes(currentState);

  return groupMatch && stateMatch;
}

/**
 * Get the next state after successful tool execution.
 */
export function getNextState(tool: AgentTool, currentState: string): string {
  const nextState = tool.config?.["state"] as string | undefined;
  return nextState ?? currentState;
}
