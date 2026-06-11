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
  NodeRuntime,
} from "@effect/platform-node";
import type {
  ProcessorConfig,
  FlowContext,
  FlowProcessorRuntime,
  AgentRequest,
  AgentResponse,
  TextCompletionRequest,
  TextCompletionResponse,
  GraphRagRequest,
  GraphRagResponse,
  DocumentRagRequest,
  DocumentRagResponse,
  TriplesQueryRequest,
  TriplesQueryResponse,
  ToolRequest,
  ToolResponse,
  EffectConfigHandler,
  FlowResourceNotFoundError,
  MessagingDeliveryError,
  Spec,
} from "@trustgraph/base";
import {
  makeFlowProcessor,
  makeConsumerSpec,
  makeProducerSpec,
  makeRequestResponseSpec,
  makeFlowProcessorProgram,
  errorMessage,
} from "@trustgraph/base";
import {Context, Effect, Layer, Match, Ref} from "effect";
import * as O from "effect/Option";
import * as Predicate from "effect/Predicate";
import * as S from "effect/Schema";
import type {
  ExplainData,
} from "./tools.js";
import {
  createKnowledgeQueryTool,
  createDocumentQueryTool,
  createTriplesQueryTool,
  createMcpTool,
} from "./tools.js";
import { buildReActPrompt } from "./prompt.js";
import { filterToolsByGroupAndState } from "../tool-filter.js";
import type { AgentTool, ToolArg } from "./types.js";

const MAX_ITERATIONS = 10;

const AgentResponseProducer = makeProducerSpec<AgentResponse>("agent-response");
const AgentLlmClient = makeRequestResponseSpec<TextCompletionRequest, TextCompletionResponse>(
  "llm",
  "text-completion-request",
  "text-completion-response",
);
const AgentGraphRagClient = makeRequestResponseSpec<GraphRagRequest, GraphRagResponse>(
  "graph-rag",
  "graph-rag-request",
  "graph-rag-response",
);
const AgentDocRagClient = makeRequestResponseSpec<DocumentRagRequest, DocumentRagResponse>(
  "doc-rag",
  "document-rag-request",
  "document-rag-response",
);
const AgentTriplesClient = makeRequestResponseSpec<TriplesQueryRequest, TriplesQueryResponse>(
  "triples",
  "triples-request",
  "triples-response",
);
const AgentMcpToolClient = makeRequestResponseSpec<ToolRequest, ToolResponse>(
  "mcp-tool",
  "mcp-tool-request",
  "mcp-tool-response",
);

const UnknownRecord = S.Record(S.String, S.Unknown);
const ToolArgumentConfig = S.StructWithRest(
  S.Struct({
    name: S.optionalKey(S.String),
    type: S.optionalKey(S.String),
    description: S.optionalKey(S.String),
  }),
  [UnknownRecord],
);
const ToolConfigEntry = S.StructWithRest(
  S.Struct({
    type: S.optionalKey(S.String),
    name: S.optionalKey(S.String),
    description: S.optionalKey(S.String),
    arguments: ToolArgumentConfig.pipe(S.Array, S.optionalKey),
  }),
  [UnknownRecord],
);
type ToolConfigEntry = typeof ToolConfigEntry.Type;

const decodeRawToolConfig = S.decodeUnknownOption(S.Record(S.String, S.String));
const decodeToolConfigEntry = S.decodeUnknownOption(ToolConfigEntry.pipe(S.fromJsonString));

export interface AgentRuntimeService {
  readonly configureTools: (
    config: Record<string, unknown>,
    version: number,
  ) => Effect.Effect<void>;
  readonly getConfiguredTools: Effect.Effect<ReadonlyArray<AgentTool> | null>;
}

export class AgentRuntime extends Context.Service<AgentRuntime, AgentRuntimeService>()(
  "@trustgraph/flow/agent/react/service/AgentRuntime",
) {}

const buildConfiguredTool = Effect.fn("AgentService.buildConfiguredTool")(function* (
  toolId: string,
  data: ToolConfigEntry,
) {
  const implType = data.type ?? "";
  const name = data.name ?? "";
  const description = data.description ?? "";
  const config: Record<string, unknown> = { ...data };

  if (name.length === 0) {
    yield* Effect.logWarning(`[AgentService] Skipping tool with no name: ${toolId}`);
    return null;
  }

  return yield* Match.value(implType).pipe(
    Match.when("knowledge-query", () =>
      Effect.succeed({
        name,
        description:
          description.length > 0
            ? description
            : "Query the knowledge graph for information about entities and their relationships.",
        args: [{ name: "question", type: "string", description: "The question to ask" }],
        config,
        execute: () => Effect.succeed(""),
      })
    ),

    Match.when("document-query", () =>
      Effect.succeed({
        name,
        description:
          description.length > 0
            ? description
            : "Search documents for relevant information.",
        args: [{ name: "question", type: "string", description: "The question to search for" }],
        config,
        execute: () => Effect.succeed(""),
      })
    ),

    Match.when("triples-query", () =>
      Effect.succeed({
        name,
        description:
          description.length > 0
            ? description
            : "Query for specific triples in the knowledge graph.",
        args: [
          { name: "subject", type: "string", description: "Subject entity (optional)" },
          { name: "predicate", type: "string", description: "Predicate/relationship (optional)" },
          { name: "object", type: "string", description: "Object entity (optional)" },
        ],
        config,
        execute: () => Effect.succeed(""),
      })
    ),

    Match.when("mcp-tool", () => {
      const args: ToolArg[] = (data.arguments ?? []).map((arg) => ({
        name: arg.name ?? "",
        type: arg.type ?? "string",
        description: arg.description ?? "",
      }));

      return Effect.succeed({
        name,
        description,
        args,
        config,
        execute: () => Effect.succeed(""),
      });
    }),

    Match.orElse(() =>
      Effect.logWarning(`[AgentService] Unknown tool type "${implType}" for ${name}`).pipe(
        Effect.as(null),
      )
    ),
  );
});

const loadConfiguredTools = Effect.fn("AgentRuntime.loadConfiguredTools")(function* (
  config: Record<string, unknown>,
  version: number,
) {
  yield* Effect.log(`[AgentService] Loading tool configuration version ${version}`);

  if (!("tool" in config) || typeof config.tool !== "object" || config.tool === null) {
    yield* Effect.log("[AgentService] No tool config found, using default tools");
    return null;
  }

  const rawConfig = decodeRawToolConfig(config.tool);
  if (O.isNone(rawConfig)) {
    yield* Effect.logError("[AgentService] Tool config must be an object of JSON strings");
    return null;
  }

  const tools: AgentTool[] = [];
  for (const [toolId, toolValue] of Object.entries(rawConfig.value)) {
    const decoded = decodeToolConfigEntry(toolValue);
    if (O.isNone(decoded)) {
      yield* Effect.logError(`[AgentService] Failed to parse tool config ${toolId}`);
      continue;
    }

    const tool = yield* buildConfiguredTool(toolId, decoded.value);
    if (tool === null) continue;

    tools.push(tool);
    yield* Effect.log(`[AgentService] Registered tool: ${tool.name} (${tool.config?.type ?? "unknown"})`);
  }

  yield* Effect.log(`[AgentService] ${tools.length} tools loaded from config`);
  return tools.length > 0 ? tools : null;
});

export const makeAgentRuntime = Effect.gen(function* () {
  const configuredToolsRef = yield* Ref.make<ReadonlyArray<AgentTool> | null>(null);

  return AgentRuntime.of({
    configureTools: Effect.fn("AgentRuntime.configureTools")(function* (config, version) {
      const tools = yield* loadConfiguredTools(config, version);
      yield* Ref.set(configuredToolsRef, tools);
    }),
    getConfiguredTools: Ref.get(configuredToolsRef),
  });
});

export const AgentRuntimeLive = Layer.effect(AgentRuntime, makeAgentRuntime);

const onToolsConfig = Effect.fn("AgentService.onToolsConfig")(function* (
  config: Record<string, unknown>,
  version: number,
) {
  const runtime = yield* AgentRuntime;
  yield* runtime.configureTools(config, version);
});

const wireTools = Effect.fn("AgentService.wireTools")(function* (
  tools: ReadonlyArray<AgentTool>,
  flowCtx: FlowContext<AgentRuntime>,
  collection: string | undefined,
  onExplain: (data: ExplainData) => void,
) {
  const graphRag = yield* flowCtx.flow.requestorEffect(AgentGraphRagClient);
  const docRag = yield* flowCtx.flow.requestorEffect(AgentDocRagClient);
  const triples = yield* flowCtx.flow.requestorEffect(AgentTriplesClient);
  const mcpTool = yield* flowCtx.flow.requestorEffect(AgentMcpToolClient);

  return tools.map((tool) => {
    const rawImplType = tool.config?.type;
    const implType = Predicate.isString(rawImplType) ? rawImplType : undefined;

    return Match.value(implType).pipe(
      Match.when("knowledge-query", () => {
        const live = createKnowledgeQueryTool(
          graphRag,
          collection,
          onExplain,
        );
        return { ...tool, execute: live.execute };
      }),
      Match.when("document-query", () => {
        const live = createDocumentQueryTool(
          docRag,
          collection,
        );
        return { ...tool, execute: live.execute };
      }),
      Match.when("triples-query", () => {
        const live = createTriplesQueryTool(
          triples,
          collection,
        );
        return { ...tool, execute: live.execute };
      }),
      Match.when("mcp-tool", () => {
        const live = createMcpTool(
          mcpTool,
          tool.name,
          tool.description,
          tool.args,
        );
        return { ...tool, execute: live.execute };
      }),
      Match.orElse(() => tool),
    );
  });
});

const defaultTools = Effect.fn("AgentService.defaultTools")(function* (
  flowCtx: FlowContext<AgentRuntime>,
  collection: string | undefined,
  onExplain: (data: ExplainData) => void,
) {
  const graphRag = yield* flowCtx.flow.requestorEffect(AgentGraphRagClient);
  const docRag = yield* flowCtx.flow.requestorEffect(AgentDocRagClient);
  const triples = yield* flowCtx.flow.requestorEffect(AgentTriplesClient);

  return [
    createKnowledgeQueryTool(
      graphRag,
      collection,
      onExplain,
    ),
    createDocumentQueryTool(
      docRag,
      collection,
    ),
    createTriplesQueryTool(
      triples,
      collection,
    ),
  ];
});

const executeTool = (
  tool: AgentTool,
  input: string,
): Effect.Effect<string> =>
  tool.execute(input).pipe(
    Effect.catch((cause) =>
      Effect.succeed(`Error executing tool: ${errorMessage(cause)}`),
    ),
  );

type AgentHandlerError =
  | FlowResourceNotFoundError
  | MessagingDeliveryError;

const onAgentRequest = Effect.fn("AgentService.onRequest")(function* (
  msg: AgentRequest,
  properties: Record<string, string>,
  flowCtx: FlowContext<AgentRuntime>,
): Effect.fn.Return<void, AgentHandlerError, AgentRuntime> {
  const requestId = properties.id;
  if (requestId === undefined || requestId.length === 0) return;

  const responseProducer = yield* flowCtx.flow.producerEffect(AgentResponseProducer);

  yield* Effect.gen(function* () {
    const runtime = yield* AgentRuntime;
    const explainEvents: ExplainData[] = [];
    const onExplain = (data: ExplainData) => {
      explainEvents.push(data);
    };

    const configuredTools = yield* runtime.getConfiguredTools;
    let tools = configuredTools !== null
      ? yield* wireTools(configuredTools, flowCtx, msg.collection, onExplain)
      : yield* defaultTools(flowCtx, msg.collection, onExplain);

    tools = filterToolsByGroupAndState(tools, msg.group, msg.state);

    const { system, prompt: initialPrompt } = buildReActPrompt(
      tools,
      msg.question,
    );

    const llmClient = yield* flowCtx.flow.requestorEffect(AgentLlmClient);

    let conversation = initialPrompt;

    for (let iteration = 0; iteration < MAX_ITERATIONS; iteration++) {
      yield* Effect.log(
        `[AgentService] Iteration ${iteration + 1}/${MAX_ITERATIONS} for request ${requestId}`,
      );

      const llmResponse = yield* llmClient.request({
        system,
        prompt: conversation,
      });

      if (llmResponse.error !== undefined) {
        yield* responseProducer.send(requestId, {
          chunk_type: "error",
          content: `LLM error: ${llmResponse.error.message}`,
          end_of_dialog: true,
        });
        return;
      }

      const text = llmResponse.response;
      const parsed = parseReActResponse(text);

      if (parsed.thought.length > 0) {
        yield* responseProducer.send(requestId, {
          chunk_type: "thought",
          content: parsed.thought,
          end_of_message: true,
        });
      }

      if (parsed.finalAnswer.length > 0) {
        for (const explain of explainEvents) {
          yield* responseProducer.send(requestId, {
            chunk_type: "explain",
            content: "",
            explain_id: explain.explainId,
            explain_triples: [...explain.triples],
          });
        }

        yield* responseProducer.send(requestId, {
          chunk_type: "answer",
          content: parsed.finalAnswer,
          end_of_message: true,
          end_of_dialog: true,
        });
        return;
      }

      if (parsed.action.length > 0 && parsed.actionInput.length > 0) {
        const tool = tools.find((candidate) => candidate.name === parsed.action);
        const observation = tool === undefined
          ? `Unknown tool: ${parsed.action}. Available tools: ${tools.map((candidate) => candidate.name).join(", ")}`
          : yield* executeTool(tool, parsed.actionInput);

        yield* responseProducer.send(requestId, {
          chunk_type: "observation",
          content: observation,
          end_of_message: true,
        });

        conversation += `\n${text}\nObservation: ${observation}\n`;
      } else if (parsed.finalAnswer.length === 0) {
        conversation += `\n${text}\nObservation: You must either use a tool (Action + Action Input) or provide a Final Answer.\n`;
      }
    }

    yield* responseProducer.send(requestId, {
      chunk_type: "error",
      content:
        "Maximum reasoning iterations reached without a final answer. " +
        "The agent was unable to complete the task within the allowed steps.",
      end_of_message: true,
      end_of_dialog: true,
    });
  }).pipe(
    Effect.catch((error: unknown) =>
      Effect.logError(`[AgentService] Error processing request ${requestId}`, {
        error: errorMessage(error),
      }).pipe(
        Effect.flatMap(() =>
          responseProducer.send(requestId, {
            chunk_type: "error",
            content: `Agent error: ${errorMessage(error)}`,
            end_of_message: true,
            end_of_dialog: true,
          }),
        ),
      ),
    ),
  );
});

export const makeAgentSpecs = (): ReadonlyArray<Spec<AgentRuntime>> => [
  makeConsumerSpec<AgentRequest, AgentHandlerError, AgentRuntime>(
    "agent-request",
    onAgentRequest,
  ),
  AgentResponseProducer,
  AgentLlmClient,
  AgentGraphRagClient,
  AgentDocRagClient,
  AgentTriplesClient,
  AgentMcpToolClient,
];

export const makeAgentConfigHandlers = (): ReadonlyArray<
  EffectConfigHandler<never, AgentRuntime>
> => [onToolsConfig];

export type AgentService = FlowProcessorRuntime<AgentRuntime>;

export function makeAgentService(config: ProcessorConfig): AgentService {
  const service = makeFlowProcessor(config, {
    specifications: makeAgentSpecs(),
    provide: (effect) => effect.pipe(
      Effect.provideServiceEffect(AgentRuntime, makeAgentRuntime),
    ),
  });
  service.registerConfigHandler(onToolsConfig);
  return service;
}

export const AgentService = makeAgentService;

/**
 * Simple line-based parser for ReAct LLM output.
 *
 * Extracts Thought, Action, Action Input, and Final Answer sections.
 * For the MVP this avoids the complexity of the streaming parser --
 * we parse the complete response at once.
 */
export function parseReActResponse(text: string): {
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
      finalAnswer =
        firstLine + (remainingLines.length > 0 ? `\n${remainingLines}` : "");
      break;
    }if (trimmed.startsWith("Thought:")) {
      currentSection = "thought";
      const content = trimmed.slice("Thought:".length).trim();
      if (content.length > 0) {
        thought += (thought.length > 0 ? "\n" : "") + content;
      }
    } else if (trimmed.startsWith("Action Input:")) {
      currentSection = "action_input";
      const content = trimmed.slice("Action Input:".length).trim();
      if (content.length > 0) {
        actionInput += content;
      }
    } else if (trimmed.startsWith("Action:")) {
      currentSection = "action";
      const content = trimmed.slice("Action:".length).trim();
      if (content.length > 0) {
        action = content;
      }
    } else if (trimmed.startsWith("Observation:")) {
      // Stop processing -- observations are injected by us, not the LLM
      currentSection = null;
    } else if (trimmed.length > 0 && currentSection !== null) {
      // Continuation line for current section
      Match.value(currentSection).pipe(
        Match.when("thought", () => {
          thought += `\n${trimmed}`;
        }),
        Match.when("action", () => {
          // Action should be a single line (tool name), but handle multi-line
          action += ` ${trimmed}`;
        }),
        Match.when("action_input", () => {
          actionInput += `\n${trimmed}`;
        }),
        Match.exhaustive,
      );
    }
  }

  return {
    thought: thought.trim(),
    action: action.trim(),
    actionInput: actionInput.trim(),
    finalAnswer: finalAnswer.trim(),
  };
}

export const program = makeFlowProcessorProgram<ProcessorConfig, never, AgentRuntime>({
  id: "agent",
  specs: () => makeAgentSpecs(),
  configHandlers: () => makeAgentConfigHandlers(),
  layer: () => AgentRuntimeLive,
});

export function runMain(): void {
  NodeRuntime.runMain(program);
}
