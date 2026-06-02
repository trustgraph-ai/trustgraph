/**
 * MCP tool-calling service — calls external MCP tool servers.
 *
 * Receives ToolRequest (name + JSON-encoded parameters) over NATS,
 * connects to the appropriate MCP server via the MCP SDK,
 * invokes the tool, and returns the result as a ToolResponse.
 *
 * MCP service configs are pushed via the config system under the "mcp" key.
 *
 * Python reference: trustgraph-flow/trustgraph/agent/mcp_tool/service.py
 */

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";
import { NodeRuntime } from "@effect/platform-node";

import {
  makeFlowProcessor,
  makeConsumerSpec,
  makeProducerSpec,
  makeFlowProcessorProgram,
  errorMessage,
  type ProcessorConfig,
  type FlowContext,
  type FlowProcessorRuntime,
  type ToolRequest,
  type ToolResponse,
  type EffectConfigHandler,
  type FlowResourceNotFoundError,
  type MessagingDeliveryError,
  type Spec,
} from "@trustgraph/base";
import { Context, Effect, Layer, ManagedRuntime, Ref } from "effect";
import * as O from "effect/Option";
import * as S from "effect/Schema";

const McpServiceConfig = S.Struct({
  url: S.String,
  "remote-name": S.optionalKey(S.String),
  "auth-token": S.optionalKey(S.String),
});
type McpServiceConfig = typeof McpServiceConfig.Type;

const decodeRawMcpConfig = S.decodeUnknownOption(S.Record(S.String, S.String));
const decodeMcpServiceConfig = S.decodeUnknownOption(McpServiceConfig.pipe(S.fromJsonString));
const decodeToolParameters = S.decodeUnknownOption(S.Record(S.String, S.Unknown).pipe(S.fromJsonString));
const encodeJson = S.encodeUnknownOption(S.UnknownFromJsonString);

export class McpToolError extends S.TaggedErrorClass<McpToolError>()(
  "McpToolError",
  {
    message: S.String,
    operation: S.String,
    tool: S.optionalKey(S.String),
  },
) {}

export interface McpToolRuntimeService {
  readonly configure: (
    config: Record<string, unknown>,
    version: number,
  ) => Effect.Effect<void>;
  readonly invokeTool: (
    name: string,
    parameters: Record<string, unknown>,
  ) => Effect.Effect<string | unknown, McpToolError>;
}

export class McpToolRuntime extends Context.Service<
  McpToolRuntime,
  McpToolRuntimeService
>()("@trustgraph/flow/agent/mcp-tool/service/McpToolRuntime") {}

const McpToolResponseProducer = makeProducerSpec<ToolResponse>("mcp-tool-response");

const mcpToolError = (
  operation: string,
  cause: unknown,
  tool?: string,
): McpToolError =>
  McpToolError.make({
    operation,
    message: errorMessage(cause),
    ...(tool === undefined ? {} : { tool }),
  });

const closeTransport = (
  transport: StreamableHTTPClientTransport,
  tool: string,
) =>
  Effect.tryPromise({
    try: () => transport.close(),
    catch: (cause) => mcpToolError("close-transport", cause, tool),
  }).pipe(
    Effect.catch((error) =>
      Effect.logError("[McpToolService] Failed to close MCP transport", {
        error: error.message,
        tool: error.tool ?? tool,
      }),
    ),
  );

const loadMcpServices = Effect.fn("McpToolRuntime.loadMcpServices")(function* (
  config: Record<string, unknown>,
  version: number,
) {
  yield* Effect.log(`[McpToolService] Got config version ${version}`);

  if (!("mcp" in config) || typeof config.mcp !== "object" || config.mcp === null) {
    return {};
  }

  const rawConfig = decodeRawMcpConfig(config.mcp);
  if (O.isNone(rawConfig)) {
    yield* Effect.logError("[McpToolService] MCP config must be an object of JSON strings");
    return {};
  }

  const services: Record<string, McpServiceConfig> = {};
  for (const [name, value] of Object.entries(rawConfig.value)) {
    const decoded = decodeMcpServiceConfig(value);
    if (O.isNone(decoded)) {
      yield* Effect.logError(`[McpToolService] Failed to parse MCP config for ${name}`);
      continue;
    }
    services[name] = decoded.value;
    yield* Effect.log(`[McpToolService] Registered MCP service: ${name}`);
  }

  yield* Effect.log(
    `[McpToolService] ${Object.keys(services).length} MCP services configured`,
  );

  return services;
});

const invokeConfiguredTool = Effect.fn("McpToolRuntime.invokeTool")(function* (
  services: Record<string, McpServiceConfig>,
  name: string,
  parameters: Record<string, unknown>,
) {
  if (!(name in services)) {
    return yield* mcpToolError("lookup-service", `MCP service "${name}" not known`, name);
  }

  const svcConfig = services[name];
  if (svcConfig.url.length === 0) {
    return yield* mcpToolError("validate-service", `MCP service "${name}" URL not defined`, name);
  }

  const remoteName = svcConfig["remote-name"] ?? name;
  const headers: Record<string, string> = {};
  if (svcConfig["auth-token"] !== undefined && svcConfig["auth-token"].length > 0) {
    headers.Authorization = `Bearer ${svcConfig["auth-token"]}`;
  }

  yield* Effect.log(`[McpToolService] Invoking ${remoteName} at ${svcConfig.url}`);

  const url = yield* Effect.try({
    try: () => new URL(svcConfig.url),
    catch: (cause) => mcpToolError("validate-url", cause, name),
  });

  const transport = new StreamableHTTPClientTransport(
    url,
    { requestInit: { headers } },
  );
  const client = new Client({ name: "trustgraph-mcp-client", version: "1.0.0" });

  const result = yield* Effect.acquireUseRelease(
    Effect.tryPromise({
      try: () => client.connect(transport as unknown as Parameters<Client["connect"]>[0]),
      catch: (cause) => mcpToolError("connect", cause, name),
    }).pipe(Effect.as(client)),
    (connectedClient) =>
      Effect.tryPromise({
        try: () =>
          connectedClient.callTool({
            name: remoteName,
            arguments: parameters,
          }),
        catch: (cause) => mcpToolError("call-tool", cause, name),
      }),
    () => closeTransport(transport, name),
  );

  if (result.structuredContent !== undefined && result.structuredContent !== null) {
    return result.structuredContent;
  }

  if (result.content !== undefined && Array.isArray(result.content)) {
    return result.content
      .filter((c): c is { type: "text"; text: string } => c.type === "text")
      .map((c) => c.text)
      .join("");
  }

  return "No content";
});

export const makeMcpToolRuntime = Effect.gen(function* () {
  const servicesRef = yield* Ref.make<Record<string, McpServiceConfig>>({});

  return McpToolRuntime.of({
    configure: Effect.fn("McpToolRuntime.configure")(function* (config, version) {
      const services = yield* loadMcpServices(config, version);
      yield* Ref.set(servicesRef, services);
    }),
    invokeTool: Effect.fn("McpToolRuntime.invokeToolFromRef")(function* (name, parameters) {
      const services = yield* Ref.get(servicesRef);
      return yield* invokeConfiguredTool(services, name, parameters);
    }),
  });
});

export const McpToolRuntimeLive = Layer.effect(McpToolRuntime, makeMcpToolRuntime);

const onMcpConfig = Effect.fn("McpToolService.onConfig")(function* (
  config: Record<string, unknown>,
  version: number,
) {
  const runtime = yield* McpToolRuntime;
  yield* runtime.configure(config, version);
});

type McpToolHandlerError =
  | FlowResourceNotFoundError
  | MessagingDeliveryError;

const parametersFromJson = (
  name: string,
  parameters: string,
): Effect.Effect<Record<string, unknown>, McpToolError> => {
  if (parameters.length === 0) return Effect.succeed({});

  const decoded = decodeToolParameters(parameters);
  if (O.isNone(decoded)) {
    return Effect.fail(mcpToolError("decode-parameters", "Tool parameters must be a JSON object", name));
  }
  return Effect.succeed(decoded.value);
};

const onMcpToolRequest = Effect.fn("McpToolService.onRequest")(function* (
  msg: ToolRequest,
  properties: Record<string, string>,
  flowCtx: FlowContext<McpToolRuntime>,
): Effect.fn.Return<void, McpToolHandlerError, McpToolRuntime> {
  const requestId = properties.id;
  if (requestId === undefined || requestId.length === 0) return;

  const responseProducer = yield* flowCtx.flow.producerEffect(McpToolResponseProducer);
  const runtime = yield* McpToolRuntime;

  const result = yield* parametersFromJson(msg.name, msg.parameters).pipe(
    Effect.flatMap((parameters) => runtime.invokeTool(msg.name, parameters)),
    Effect.catch((error) =>
      Effect.logError(`[McpToolService] Error invoking tool ${msg.name}`, {
        error: error.message,
        operation: error.operation,
      }).pipe(
        Effect.flatMap(() =>
          responseProducer.send(requestId, {
            error: { type: "tool-error", message: error.message },
          }),
        ),
        Effect.as(undefined),
      ),
    ),
  );

  if (result === undefined) return;

  if (typeof result === "string") {
    yield* responseProducer.send(requestId, { text: result });
    return;
  }

  const encoded = encodeJson(result);
  yield* responseProducer.send(requestId, {
    object: O.isSome(encoded) ? encoded.value : String(result),
  });
});

export const makeMcpToolSpecs = (): ReadonlyArray<Spec<McpToolRuntime>> => [
  makeConsumerSpec<ToolRequest, McpToolHandlerError, McpToolRuntime>(
    "mcp-tool-request",
    onMcpToolRequest,
  ),
  McpToolResponseProducer,
];

export const makeMcpToolConfigHandlers = (): ReadonlyArray<
  EffectConfigHandler<never, McpToolRuntime>
> => [onMcpConfig];

export type McpToolService = FlowProcessorRuntime<McpToolRuntime>;

export function makeMcpToolService(config: ProcessorConfig): McpToolService {
  const runtime = Effect.runSync(makeMcpToolRuntime);
  const service = makeFlowProcessor(config, {
    specifications: makeMcpToolSpecs(),
    provide: (effect) => effect.pipe(Effect.provideService(McpToolRuntime, runtime)),
  });
  service.registerConfigHandler((pushedConfig, version) =>
    Effect.runPromise(onMcpConfig(pushedConfig, version).pipe(
      Effect.provideService(McpToolRuntime, runtime),
    )),
  );
  return service;
}

export const McpToolService = makeMcpToolService;

export const program = makeFlowProcessorProgram<ProcessorConfig, never, McpToolRuntime>({
  id: "mcp-tool",
  specs: () => makeMcpToolSpecs(),
  configHandlers: () => makeMcpToolConfigHandlers(),
  layer: () => McpToolRuntimeLive,
});

const mcpToolRuntime = ManagedRuntime.make(Layer.empty);

export function run(): Promise<void> {
  return mcpToolRuntime.runPromise(program);
}

export function runMain(): void {
  NodeRuntime.runMain(program);
}
