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
 * Tools can be registered statically (hardcoded fallback) or dynamically via
 * config-push. When a "tool" section is present in config, tools are built
 * from that config; otherwise the 3 default tools are used for backward compat.
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
  type ToolRequest,
  type ToolResponse,
} from "@trustgraph/base";

import {
  createKnowledgeQueryTool,
  createDocumentQueryTool,
  createTriplesQueryTool,
  createMcpTool,
} from "./tools.js";
import { buildReActPrompt } from "./prompt.js";
import { filterToolsByGroupAndState, getNextState } from "../tool-filter.js";
import type { AgentTool, ToolArg } from "./types.js";

const MAX_ITERATIONS = 10;

export class AgentService extends FlowProcessor {
  /** Config-driven tools; null means "use hardcoded fallback". */
  private configuredTools: AgentTool[] | null = null;

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

    // MCP tool invocation client
    this.registerSpecification(
      new RequestResponseSpec<ToolRequest, ToolResponse>(
        "mcp-tool",
        "mcp-tool-request",
        "mcp-tool-response",
      ),
    );

    // Register for config-push to build tools dynamically
    this.registerConfigHandler(this.onToolsConfig.bind(this));

    console.log("[AgentService] Service initialized");
  }

  // ---------- Config-driven tool registration ----------

  private async onToolsConfig(
    config: Record<string, unknown>,
    version: number,
  ): Promise<void> {
    console.log(`[AgentService] Loading tool configuration version ${version}`);

    try {
      if (!("tool" in config) || typeof config.tool !== "object" || config.tool === null) {
        // No tool config — keep using hardcoded fallback
        this.configuredTools = null;
        console.log("[AgentService] No tool config found, using default tools");
        return;
      }

      const toolConfig = config.tool as Record<string, string>;
      const tools: AgentTool[] = [];

      for (const [_toolId, toolValue] of Object.entries(toolConfig)) {
        try {
          const data = JSON.parse(toolValue) as Record<string, unknown>;
          const implType = data["type"] as string;
          const name = data["name"] as string;
          const description = data["description"] as string ?? "";

          if (!name) {
            console.warn(`[AgentService] Skipping tool with no name: ${_toolId}`);
            continue;
          }

          let tool: AgentTool | null = null;

          switch (implType) {
            case "knowledge-query":
              // Will be wired to requestor at request time
              tool = {
                name,
                description: description || "Query the knowledge graph for information about entities and their relationships.",
                args: [{ name: "question", type: "string", description: "The question to ask" }],
                config: data,
                execute: async () => "", // placeholder — wired at request time
              };
              break;

            case "document-query":
              tool = {
                name,
                description: description || "Search documents for relevant information.",
                args: [{ name: "question", type: "string", description: "The question to search for" }],
                config: data,
                execute: async () => "",
              };
              break;

            case "triples-query":
              tool = {
                name,
                description: description || "Query for specific triples in the knowledge graph.",
                args: [
                  { name: "subject", type: "string", description: "Subject entity (optional)" },
                  { name: "predicate", type: "string", description: "Predicate/relationship (optional)" },
                  { name: "object", type: "string", description: "Object entity (optional)" },
                ],
                config: data,
                execute: async () => "",
              };
              break;

            case "mcp-tool": {
              const configArgs = (data["arguments"] as Array<Record<string, string>>) ?? [];
              const args: ToolArg[] = configArgs.map((a) => ({
                name: a.name ?? "",
                type: a.type ?? "string",
                description: a.description ?? "",
              }));

              // Create a placeholder — will be wired to the MCP requestor at request time
              tool = {
                name,
                description,
                args,
                config: data,
                execute: async () => "", // placeholder
              };
              break;
            }

            default:
              console.warn(`[AgentService] Unknown tool type "${implType}" for ${name}`);
              continue;
          }

          if (tool) {
            tools.push(tool);
            console.log(`[AgentService] Registered tool: ${name} (${implType})`);
          }
        } catch (err) {
          console.error(`[AgentService] Failed to parse tool config ${_toolId}:`, err);
        }
      }

      this.configuredTools = tools.length > 0 ? tools : null;
      console.log(`[AgentService] ${tools.length} tools loaded from config`);
    } catch (err) {
      console.error("[AgentService] Config reload failed:", err);
    }
  }

  /**
   * Wire up tool execute functions with live requestors from the flow context.
   * Config-driven tools store placeholders; this replaces them with real impls.
   */
  private wireTools(tools: AgentTool[], flowCtx: FlowContext, collection?: string): AgentTool[] {
    return tools.map((tool) => {
      const implType = tool.config?.["type"] as string | undefined;

      switch (implType) {
        case "knowledge-query": {
          const live = createKnowledgeQueryTool(
            flowCtx.flow.requestor<GraphRagRequest, GraphRagResponse>("graph-rag"),
            collection,
          );
          return { ...tool, execute: live.execute };
        }
        case "document-query": {
          const live = createDocumentQueryTool(
            flowCtx.flow.requestor<DocumentRagRequest, DocumentRagResponse>("doc-rag"),
            collection,
          );
          return { ...tool, execute: live.execute };
        }
        case "triples-query": {
          const live = createTriplesQueryTool(
            flowCtx.flow.requestor<TriplesQueryRequest, TriplesQueryResponse>("triples"),
            collection,
          );
          return { ...tool, execute: live.execute };
        }
        case "mcp-tool": {
          const live = createMcpTool(
            flowCtx.flow.requestor<ToolRequest, ToolResponse>("mcp-tool"),
            tool.name,
            tool.description,
            tool.args,
          );
          return { ...tool, execute: live.execute };
        }
        default:
          return tool;
      }
    });
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
      // Build tools — config-driven or hardcoded fallback
      let tools: AgentTool[];

      if (this.configuredTools) {
        tools = this.wireTools(this.configuredTools, flowCtx, msg.collection);
      } else {
        // Hardcoded fallback (backward compat)
        tools = [
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
      }

      // Apply tool filtering by group and state
      tools = filterToolsByGroupAndState(tools, msg.group, msg.state);

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
