/**
 * TrustGraph MCP stdio compatibility server.
 *
 * This keeps the original @modelcontextprotocol/sdk entry points available,
 * while moving gateway calls, callback bridging, JSON encoding, and config
 * reads behind Effect values.
 */

import {McpServer} from "@modelcontextprotocol/sdk/server/mcp.js";
import {StdioServerTransport} from "@modelcontextprotocol/sdk/server/stdio.js";
import {NodeRuntime} from "@effect/platform-node";
import {createTrustGraphSocket, type BaseApi, type Term} from "@trustgraph/client";
import {Effect, Layer, ManagedRuntime} from "effect";
import * as Predicate from "effect/Predicate";
import * as S from "effect/Schema";
import {z} from "zod";
import {loadTrustGraphMcpConfig} from "./server-effect.js";

interface ToolTextContent {
  readonly type: "text"
  readonly text: string
}

interface ToolTextResult extends Record<string, unknown> {
  readonly content: Array<ToolTextContent>
}

class StdioMcpError extends S.TaggedErrorClass<StdioMcpError>()(
  "StdioMcpError",
  {
    cause: S.DefectWithStack,
    message: S.String,
  },
) {
}

const encodeJsonText = S.encodeUnknownEffect(S.UnknownFromJsonString);

const toErrorMessage = (cause: unknown): string => {
  if (Predicate.isError(cause) && cause.message.length > 0) {
    return cause.message;
  }
  if (Predicate.isString(cause) && cause.length > 0) {
    return cause;
  }
  if (Predicate.isObject(cause) && Predicate.hasProperty(cause, "message") && Predicate.isString(cause.message) && cause.message.length > 0) {
    return cause.message;
  }
  return "TrustGraph MCP stdio operation failed";
};

const stdioMcpError = (cause: unknown) =>
  StdioMcpError.make({cause, message: toErrorMessage(cause)});

const textResult = (text: string): ToolTextResult => ({
  content: [{type: "text", text}],
});

const gatewayRequest = <A>(request: () => Promise<A>) =>
  Effect.tryPromise({
    try: request,
    catch: stdioMcpError,
  });

const jsonText = (value: unknown) =>
  encodeJsonText(value).pipe(
    Effect.mapError(stdioMcpError),
  );

const runTextTool = (effect: Effect.Effect<string, StdioMcpError>) =>
  Effect.runPromise(effect.pipe(Effect.map(textResult)));

const runJsonTool = (effect: Effect.Effect<unknown, StdioMcpError>) =>
  Effect.runPromise(effect.pipe(Effect.flatMap(jsonText), Effect.map(textResult)));

export function createMcpServer(config: {
  gatewayUrl: string;
  user?: string;
  token?: string;
  flowId?: string;
}) {
  const server = new McpServer({
    name: "trustgraph",
    version: "0.1.0",
  });

  const user = config.user ?? "mcp";
  const socket: BaseApi = createTrustGraphSocket(
    user,
    config.token,
    config.gatewayUrl,
  );

  const flowId = config.flowId ?? "default";

  // ===================== Flow-scoped tools =====================

  server.tool(
    "text_completion",
    "Run a text completion using the configured LLM",
    {
      system: z.string().describe("System prompt"),
      prompt: z.string().describe("User prompt"),
    },
    ({system, prompt}) =>
      runTextTool(gatewayRequest(() => socket.flow(flowId).textCompletion(system, prompt))),
  );

  server.tool(
    "graph_rag",
    "Query the knowledge graph using RAG",
    {
      query: z.string().describe("Natural language query"),
      entity_limit: z.number().optional().describe("Max entities to retrieve"),
      triple_limit: z.number().optional().describe("Max triples per entity"),
      collection: z.string().optional().describe("Collection name"),
    },
    ({query, entity_limit, triple_limit, collection}) =>
      runTextTool(
        gatewayRequest(() =>
          socket.flow(flowId).graphRag(
            query,
            {
              ...(entity_limit !== undefined ? {entityLimit: entity_limit} : {}),
              ...(triple_limit !== undefined ? {tripleLimit: triple_limit} : {}),
            },
            collection,
          )
        ),
      ),
  );

  server.tool(
    "document_rag",
    "Query documents using RAG",
    {
      query: z.string().describe("Natural language query"),
      doc_limit: z.number().optional().describe("Max documents to retrieve"),
      collection: z.string().optional().describe("Collection name"),
    },
    ({query, doc_limit, collection}) =>
      runTextTool(gatewayRequest(() => socket.flow(flowId).documentRag(query, doc_limit, collection))),
  );

  server.tool(
    "agent",
    "Ask the TrustGraph agent a question",
    {
      question: z.string().describe("Question for the agent"),
    },
    ({question}) =>
      runTextTool(
        Effect.callback<string, StdioMcpError>((resume) => {
          let fullAnswer = "";
          socket.flow(flowId).agent(
            question,
            () => {},
            () => {},
            (chunk, complete) => {
              fullAnswer += chunk;
              if (complete) {
                resume(Effect.succeed(fullAnswer));
              }
            },
            (cause) => resume(Effect.fail(stdioMcpError(cause))),
          );
        }),
      ),
  );

  server.tool(
    "embeddings",
    "Generate text embeddings",
    {
      text: z.array(z.string()).describe("Texts to embed"),
    },
    ({text}) => runJsonTool(gatewayRequest(() => socket.flow(flowId).embeddings(text))),
  );

  server.tool(
    "triples_query",
    "Query the knowledge graph for triples matching a pattern",
    {
      s: z.string().optional().describe("Subject IRI"),
      p: z.string().optional().describe("Predicate IRI"),
      o: z.string().optional().describe("Object IRI or literal"),
      limit: z.number().optional().describe("Max results"),
      collection: z.string().optional().describe("Collection name"),
    },
    ({s, p, o, limit, collection}) => {
      const sTerm: Term | undefined = s !== undefined && s.length > 0 ? {t: "i", i: s} : undefined;
      const pTerm: Term | undefined = p !== undefined && p.length > 0 ? {t: "i", i: p} : undefined;
      const oTerm: Term | undefined = o !== undefined && o.length > 0 ? {t: "i", i: o} : undefined;
      return runJsonTool(
        gatewayRequest(() => socket.flow(flowId).triplesQuery(sTerm, pTerm, oTerm, limit, collection)),
      );
    },
  );

  server.tool(
    "graph_embeddings_query",
    "Find entities similar to a text query using vector embeddings",
    {
      query: z.string().describe("Text to find similar entities for"),
      limit: z.number().optional().describe("Max results"),
      collection: z.string().optional().describe("Collection name"),
    },
    ({query, limit, collection}) =>
      runJsonTool(
        gatewayRequest(() => socket.flow(flowId).embeddings([query])).pipe(
          Effect.flatMap((vectors) =>
            gatewayRequest(() =>
              socket.flow(flowId).graphEmbeddingsQuery(
                vectors[0] ?? [],
                limit ?? 10,
                collection,
              )
            )
          ),
        ),
      ),
  );

  // ===================== Config tools =====================

  server.tool(
    "get_config_all",
    "Get all configuration values",
    {},
    () => runJsonTool(gatewayRequest(() => socket.config().getConfigAll())),
  );

  server.tool(
    "get_config",
    "Get specific configuration values",
    {
      keys: z.array(
        z.object({
          type: z.string().describe("Config type"),
          key: z.string().describe("Config key"),
        }),
      ).describe("Config keys to retrieve"),
    },
    ({keys}) => runJsonTool(gatewayRequest(() => socket.config().getConfig(keys))),
  );

  server.tool(
    "put_config",
    "Set configuration values",
    {
      values: z.array(
        z.object({
          type: z.string().describe("Config type"),
          key: z.string().describe("Config key"),
          value: z.string().describe("Config value (JSON-encoded)"),
        }),
      ).describe("Key-value entries to set"),
    },
    ({values}) => runJsonTool(gatewayRequest(() => socket.config().putConfig(values))),
  );

  server.tool(
    "delete_config",
    "Delete a configuration entry",
    {
      type: z.string().describe("Config type"),
      key: z.string().describe("Config key"),
    },
    ({type, key}) => runJsonTool(gatewayRequest(() => socket.config().deleteConfig({type, key}))),
  );

  // ===================== Flow management tools =====================

  server.tool(
    "get_flows",
    "List all available flows",
    {},
    () => runJsonTool(gatewayRequest(() => socket.flows().getFlows())),
  );

  server.tool(
    "get_flow",
    "Get a specific flow definition",
    {
      flow_id: z.string().describe("Flow ID to retrieve"),
    },
    ({flow_id}) => runJsonTool(gatewayRequest(() => socket.flows().getFlow(flow_id))),
  );

  server.tool(
    "start_flow",
    "Start a flow instance",
    {
      flow_id: z.string().describe("Flow ID"),
      blueprint_name: z.string().describe("Blueprint name"),
      description: z.string().describe("Flow description"),
      parameters: z.record(z.unknown()).optional().describe("Optional flow parameters"),
    },
    ({flow_id, blueprint_name, description, parameters}) =>
      runJsonTool(
        gatewayRequest(() => socket.flows().startFlow(flow_id, blueprint_name, description, parameters)),
      ),
  );

  server.tool(
    "stop_flow",
    "Stop a running flow",
    {
      flow_id: z.string().describe("Flow ID to stop"),
    },
    ({flow_id}) => runJsonTool(gatewayRequest(() => socket.flows().stopFlow(flow_id))),
  );

  // ===================== Library (document) tools =====================

  server.tool(
    "get_documents",
    "List all documents in the library",
    {},
    () => runJsonTool(gatewayRequest(() => socket.librarian().getDocuments())),
  );

  server.tool(
    "load_document",
    "Upload a document to the library",
    {
      document: z.string().describe("Base64-encoded document content"),
      mime_type: z.string().describe("Document MIME type"),
      title: z.string().describe("Document title"),
      comments: z.string().optional().describe("Additional comments"),
      tags: z.array(z.string()).optional().describe("Document tags"),
      id: z.string().optional().describe("Optional document ID"),
    },
    ({document, mime_type, title, comments, tags, id}) =>
      runJsonTool(
        gatewayRequest(() =>
          socket.librarian().loadDocument(
            document,
            mime_type,
            title,
            comments ?? "",
            tags ?? [],
            id,
          )
        ),
      ),
  );

  server.tool(
    "remove_document",
    "Remove a document from the library",
    {
      id: z.string().describe("Document ID to remove"),
      collection: z.string().optional().describe("Collection name"),
    },
    ({id, collection}) => runJsonTool(gatewayRequest(() => socket.librarian().removeDocument(id, collection))),
  );

  // ===================== Prompt tools =====================

  server.tool(
    "get_prompts",
    "List available prompt templates",
    {},
    () => runJsonTool(gatewayRequest(() => socket.config().getPrompts())),
  );

  server.tool(
    "get_prompt",
    "Get a specific prompt template",
    {
      id: z.string().describe("Prompt template ID"),
    },
    ({id}) => runJsonTool(gatewayRequest(() => socket.config().getPrompt(id))),
  );

  // ===================== Knowledge core tools =====================

  server.tool(
    "get_knowledge_cores",
    "List available knowledge graph cores",
    {},
    () => runJsonTool(gatewayRequest(() => socket.knowledge().getKnowledgeCores())),
  );

  server.tool(
    "delete_kg_core",
    "Delete a knowledge graph core",
    {
      id: z.string().describe("Knowledge core ID"),
      collection: z.string().optional().describe("Collection name"),
    },
    ({id, collection}) => runJsonTool(gatewayRequest(() => socket.knowledge().deleteKgCore(id, collection))),
  );

  server.tool(
    "load_kg_core",
    "Load a knowledge graph core",
    {
      id: z.string().describe("Knowledge core ID"),
      flow: z.string().describe("Flow to use for loading"),
      collection: z.string().optional().describe("Collection name"),
    },
    ({id, flow, collection}) => runJsonTool(gatewayRequest(() => socket.knowledge().loadKgCore(id, flow, collection))),
  );

  return {server, socket};
}

export const runProgram = Effect.gen(function*() {
  const config = yield* loadTrustGraphMcpConfig();
  const serverConfig = {
    gatewayUrl: config.gatewayUrl,
    user: config.user,
    flowId: config.flowId,
    ...(config.token === undefined ? {} : {token: config.token}),
  };
  const {server, socket} = createMcpServer(serverConfig);
  const transport = new StdioServerTransport();

  yield* Effect.tryPromise({
    try: () => server.connect(transport),
    catch: stdioMcpError,
  });

  yield* Effect.sync(() => {
    process.on("SIGINT", () => {
      socket.close();
      process.exit(0);
    });
  });
});

const stdioRuntime = ManagedRuntime.make(Layer.empty);

export function run(): Promise<void> {
  return stdioRuntime.runPromise(runProgram);
}

export function runMain(): void {
  NodeRuntime.runMain(runProgram);
}
