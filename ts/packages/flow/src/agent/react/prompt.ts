/**
 * Build the ReAct system prompt for the agent.
 *
 * Formats available tools into the prompt template so the LLM knows what tools
 * it can use and what format to follow.
 */

import type { AgentTool } from "./types.js";

export function buildReActPrompt(
  tools: AgentTool[],
  question: string,
): { system: string; prompt: string } {
  const toolDescriptions = tools
    .map((t) => {
      const argDesc = t.args
        .map((a) => `  - ${a.name} (${a.type}): ${a.description}`)
        .join("\n");
      return `${t.name}: ${t.description}\n  Arguments:\n${argDesc}`;
    })
    .join("\n\n");

  const toolNames = tools.map((t) => t.name).join(", ");

  const system = `You are a helpful AI assistant that answers questions using available tools.

You have access to the following tools:

${toolDescriptions}

Use this exact format for your response:

Thought: [your reasoning about what to do]
Action: [tool name, one of: ${toolNames}]
Action Input: {"argument_name": "value"}
Observation: [tool result will be inserted here]
... (repeat Thought/Action/Action Input/Observation as needed)
Thought: I now have enough information to answer.
Final Answer: [your comprehensive answer]

Important:
- Always start with a Thought.
- Action must be one of: ${toolNames}
- Action Input must be valid JSON.
- After receiving an Observation, continue with another Thought.
- When you have enough information, provide a Final Answer.
- Do NOT make up observations. Wait for the tool result.`;

  return { system, prompt: question };
}
