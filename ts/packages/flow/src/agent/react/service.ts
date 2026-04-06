/**
 * ReAct agent service -- a FlowProcessor that implements a streaming ReAct
 * (Reasoning + Acting) agent with tool execution.
 *
 * The agent:
 * 1. Receives an AgentRequest (a user question)
 * 2. Builds a ReAct prompt with available tools
 * 3. Iteratively calls the LLM, parses Thought/Action/Action Input/Final Answer
 * 4. Executes tools and feeds observations back to the LLM
 * 5. Sends streaming AgentResponse chunks (thought, observation, answer, error)
 *
 * Python reference: trustgraph-flow/trustgraph/agent/react/service.py
 */

import {
  FlowProcessor,
  ConsumerSpec,
  ProducerSpec,
  RequestResponseSpec,
  type ProcessorConfig,
  type FlowContext,
  type AgentRequest,
  type AgentResponse,
  type TextCompletionRequest,
  type TextCompletionResponse,
  type GraphRagRequest,
  type GraphRagResponse,
  type DocumentRagRequest,
  type DocumentRagResponse,
  type TriplesQueryRequest,
  type TriplesQueryResponse,
} from "@trustgraph/base";

import {
  createKnowledgeQueryTool,
  createDocumentQueryTool,
  createTriplesQueryTool,
} from "./tools.js";
import { buildReActPrompt } from "./prompt.js";
import type { AgentTool } from "./types.js";

const MAX_ITERATIONS = 10;

export class AgentService extends FlowProcessor {
  constructor(config: ProcessorConfig) {
    super(config);

    // Consumer: agent requests
    this.registerSpecification(
      new ConsumerSpec<AgentRequest>("agent-request", this.onRequest.bind(this)),
    );

    // Producer: agent responses (streaming chunks)
    this.registerSpecification(new ProducerSpec<AgentResponse>("agent-response"));

    // Request-response clients for tool execution
    this.registerSpecification(
      new RequestResponseSpec<TextCompletionRequest, TextCompletionResponse>(
        "llm",
        "text-completion-request",
        "text-completion-response",
      ),
    );
    this.registerSpecification(
      new RequestResponseSpec<GraphRagRequest, GraphRagResponse>(
        "graph-rag",
        "graph-rag-request",
        "graph-rag-response",
      ),
    );
    this.registerSpecification(
      new RequestResponseSpec<DocumentRagRequest, DocumentRagResponse>(
        "doc-rag",
        "document-rag-request",
        "document-rag-response",
      ),
    );
    this.registerSpecification(
      new RequestResponseSpec<TriplesQueryRequest, TriplesQueryResponse>(
        "triples",
        "triples-request",
        "triples-response",
      ),
    );

    console.log("[AgentService] Service initialized");
  }

  private async onRequest(
    msg: AgentRequest,
    properties: Record<string, string>,
    flowCtx: FlowContext,
  ): Promise<void> {
    const requestId = properties.id;
    if (!requestId) return;

    const responseProducer = flowCtx.flow.producer<AgentResponse>("agent-response");

    try {
      // Build tools from flow requestors
      const tools: AgentTool[] = [
        createKnowledgeQueryTool(
          flowCtx.flow.requestor<GraphRagRequest, GraphRagResponse>("graph-rag"),
          msg.collection,
        ),
        createDocumentQueryTool(
          flowCtx.flow.requestor<DocumentRagRequest, DocumentRagResponse>("doc-rag"),
          msg.collection,
        ),
        createTriplesQueryTool(
          flowCtx.flow.requestor<TriplesQueryRequest, TriplesQueryResponse>("triples"),
          msg.collection,
        ),
      ];

      // Build the ReAct prompt
      const { system, prompt: initialPrompt } = buildReActPrompt(
        tools,
        msg.question,
      );

      const llmClient = flowCtx.flow.requestor<
        TextCompletionRequest,
        TextCompletionResponse
      >("llm");

      // Conversation accumulates the full exchange for multi-turn reasoning
      let conversation = initialPrompt;

      for (let iteration = 0; iteration < MAX_ITERATIONS; iteration++) {
        console.log(
          `[AgentService] Iteration ${iteration + 1}/${MAX_ITERATIONS} for request ${requestId}`,
        );

        // Call LLM (non-streaming for MVP)
        const llmResponse = await llmClient.request({
          system,
          prompt: conversation,
        });

        if (llmResponse.error) {
          await responseProducer.send(requestId, {
            chunk_type: "error",
            content: `LLM error: ${llmResponse.error.message}`,
            end_of_dialog: true,
          });
          return;
        }

        const text = llmResponse.response;

        // Parse the LLM response with simple line-based parsing
        const parsed = parseReActResponse(text);

        // Send thought chunk
        if (parsed.thought) {
          await responseProducer.send(requestId, {
            chunk_type: "thought",
            content: parsed.thought,
            end_of_message: true,
          });
        }

        // If we got a final answer, send it and return
        if (parsed.finalAnswer) {
          await responseProducer.send(requestId, {
            chunk_type: "answer",
            content: parsed.finalAnswer,
            end_of_message: true,
            end_of_dialog: true,
          });
          return;
        }

        // Execute tool if action was specified
        if (parsed.action && parsed.actionInput) {
          const tool = tools.find((t) => t.name === parsed.action);
          let observation: string;

          if (tool) {
            try {
              observation = await tool.execute(parsed.actionInput);
            } catch (err) {
              observation = `Error executing tool: ${err instanceof Error ? err.message : String(err)}`;
            }
          } else {
            observation = `Unknown tool: ${parsed.action}. Available tools: ${tools.map((t) => t.name).join(", ")}`;
          }

          // Send observation chunk
          await responseProducer.send(requestId, {
            chunk_type: "observation",
            content: observation,
            end_of_message: true,
          });

          // Append the full exchange to conversation for the next iteration
          conversation += `\n${text}\nObservation: ${observation}\n`;
        } else if (!parsed.finalAnswer) {
          // LLM didn't produce a valid action or final answer -- nudge it
          conversation += `\n${text}\nObservation: You must either use a tool (Action + Action Input) or provide a Final Answer.\n`;
        }
      }

      // Max iterations reached without a final answer
      await responseProducer.send(requestId, {
        chunk_type: "error",
        content:
          "Maximum reasoning iterations reached without a final answer. " +
          "The agent was unable to complete the task within the allowed steps.",
        end_of_message: true,
        end_of_dialog: true,
      });
    } catch (err) {
      console.error(`[AgentService] Error processing request ${requestId}:`, err);

      await responseProducer.send(requestId, {
        chunk_type: "error",
        content: `Agent error: ${err instanceof Error ? err.message : String(err)}`,
        end_of_message: true,
        end_of_dialog: true,
      });
    }
  }
}

/**
 * Simple line-based parser for ReAct LLM output.
 *
 * Extracts Thought, Action, Action Input, and Final Answer sections.
 * For the MVP this avoids the complexity of the streaming parser --
 * we parse the complete response at once.
 */
function parseReActResponse(text: string): {
  thought: string;
  action: string;
  actionInput: string;
  finalAnswer: string;
} {
  let thought = "";
  let action = "";
  let actionInput = "";
  let finalAnswer = "";

  const lines = text.split("\n");
  let currentSection: "thought" | "action" | "action_input" | null = null;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trimStart();

    if (trimmed.startsWith("Final Answer:")) {
      // Everything from "Final Answer:" to end of text is the answer
      const firstLine = trimmed.slice("Final Answer:".length).trim();
      const remainingLines = lines.slice(i + 1).join("\n").trim();
      finalAnswer = firstLine + (remainingLines ? "\n" + remainingLines : "");
      break;
    } else if (trimmed.startsWith("Thought:")) {
      currentSection = "thought";
      const content = trimmed.slice("Thought:".length).trim();
      if (content) {
        thought += (thought ? "\n" : "") + content;
      }
    } else if (trimmed.startsWith("Action Input:")) {
      currentSection = "action_input";
      const content = trimmed.slice("Action Input:".length).trim();
      if (content) {
        actionInput += content;
      }
    } else if (trimmed.startsWith("Action:")) {
      currentSection = "action";
      const content = trimmed.slice("Action:".length).trim();
      if (content) {
        action = content;
      }
    } else if (trimmed.startsWith("Observation:")) {
      // Stop processing -- observations are injected by us, not the LLM
      currentSection = null;
    } else if (trimmed.length > 0 && currentSection) {
      // Continuation line for current section
      switch (currentSection) {
        case "thought":
          thought += "\n" + trimmed;
          break;
        case "action":
          // Action should be a single line (tool name), but handle multi-line
          action += " " + trimmed;
          break;
        case "action_input":
          actionInput += "\n" + trimmed;
          break;
      }
    }
  }

  return {
    thought: thought.trim(),
    action: action.trim(),
    actionInput: actionInput.trim(),
    finalAnswer: finalAnswer.trim(),
  };
}

export async function run(): Promise<void> {
  await AgentService.launch("agent");
}
