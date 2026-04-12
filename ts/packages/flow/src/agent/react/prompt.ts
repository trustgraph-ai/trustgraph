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

  const system = `You are a knowledge graph assistant that answers questions ONLY using data retrieved from available tools. You must NEVER use your own training knowledge to answer — only information returned by tools.

You have access to the following tools:

${toolDescriptions}

Use this exact format for your response:

Thought: [your reasoning about what to do]
Action: [tool name, one of: ${toolNames}]
Action Input: {"argument_name": "value"}
Observation: [tool result will be inserted here]
... (repeat Thought/Action/Action Input/Observation as needed)
Thought: I now have enough information to answer.
Final Answer: [your comprehensive answer based ONLY on tool observations]

Important:
- Always start with a Thought.
- Action must be one of: ${toolNames}
- Action Input must be valid JSON.
- After receiving an Observation, continue with another Thought.
- When you have enough information from tool results, provide a Final Answer.
- Do NOT make up observations. Wait for the tool result.
- Your Final Answer must be grounded ONLY in data from tool observations. If the tools did not return relevant information, your Final Answer MUST state: "The available data sources do not contain specific information about this query, so I cannot provide a grounded answer."
- NEVER supplement tool results with your own knowledge. If tool results are incomplete, say so.`;

  return { system, prompt: question };
}
