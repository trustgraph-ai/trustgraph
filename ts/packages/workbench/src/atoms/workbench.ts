import { Clipboard as BrowserClipboard } from "@effect/platform-browser";
import * as BrowserHttpClient from "@effect/platform-browser/BrowserHttpClient";
import * as BrowserKeyValueStore from "@effect/platform-browser/BrowserKeyValueStore";
import type {
  GraphRagOptions,
  BeginUploadResponse,
  ChunkedUploadDocumentMetadata,
  CompleteUploadResponse,
  ConnectionState,
  DocumentMetadata,
  ExplainEvent,
  StreamingMetadata,
  Term,
  Triple,
  UploadChunkResponse,
} from "@trustgraph/client";
import {
  DispatchPayload,
  GatewayWorkbenchHttpApi,
  TrustGraphRpcs,
} from "@trustgraph/client";
import type { Scope, } from "effect";
import { Cause, Clock, Context, Effect, Layer, Match, Metric, Option, Random, Schema as S, Stream } from "effect";
import * as A from "effect/Array";
import * as MutableHashMap from "effect/MutableHashMap";
import * as Predicate from "effect/Predicate";
import { HttpClient, HttpClientRequest } from "effect/unstable/http";
import * as Otlp from "effect/unstable/observability/Otlp";
import * as RpcClient from "effect/unstable/rpc/RpcClient";
import * as RpcSerialization from "effect/unstable/rpc/RpcSerialization";
import * as AsyncResult from "effect/unstable/reactivity/AsyncResult";
import * as Atom from "effect/unstable/reactivity/Atom";
import type * as AtomRegistry from "effect/unstable/reactivity/AtomRegistry";
import * as AtomHttpApi from "effect/unstable/reactivity/AtomHttpApi";
import * as AtomRpc from "effect/unstable/reactivity/AtomRpc";
import * as Reactivity from "effect/unstable/reactivity/Reactivity";
import * as Socket from "effect/unstable/socket/Socket";

// ---------------------------------------------------------------------------
// Browser runtime, telemetry, and generic workbench HTTP API marker
// ---------------------------------------------------------------------------

const serviceVersion = import.meta.env.VITE_APP_VERSION ?? "local";

const browserObservabilityLayer = Otlp.layerJson({
  baseUrl: "/otel",
  resource: {
    serviceName: "trustgraph-workbench",
    serviceVersion,
    attributes: {
      "trustgraph.component": "workbench",
    },
  },
  loggerExportInterval: "2 seconds",
  metricsExportInterval: "5 seconds",
  tracerExportInterval: "2 seconds",
  shutdownTimeout: "1 second",
});

class WorkbenchPromiseError extends S.TaggedErrorClass<WorkbenchPromiseError>()(
  "WorkbenchPromiseError",
  {
    cause: S.Unknown,
    message: S.String,
  },
) {}

type WorkbenchError = WorkbenchPromiseError;

const isWorkbenchPromiseError = S.is(WorkbenchPromiseError);

const ClientTriple: S.Codec<Triple, Triple> = S.suspend(() =>
  S.Struct({
    s: ClientTerm,
    p: ClientTerm,
    o: ClientTerm,
    g: S.optionalKey(S.String),
  })
);

const ClientTerm: S.Codec<Term, Term> = S.suspend(() =>
  S.Union([
    S.Struct({
      t: S.Literal("i"),
      i: S.String,
    }),
    S.Struct({
      t: S.Literal("b"),
      d: S.String,
    }),
    S.Struct({
      t: S.Literal("l"),
      v: S.String,
      dt: S.optionalKey(S.String),
      ln: S.optionalKey(S.String),
    }),
    S.Struct({
      t: S.Literal("t"),
      tr: S.optionalKey(ClientTriple),
    }),
  ])
);

const ClientExplainEvent: S.Codec<ExplainEvent, ExplainEvent> = S.Struct({
  explainId: S.String,
  explainGraph: S.String,
  explainTriples: S.optionalKey(S.Array(ClientTriple).pipe(S.mutable)),
});

function errorMessage(error: unknown): string {
  if (isWorkbenchPromiseError(error)) return error.message;
  if (Predicate.isObject(error) && Predicate.hasProperty(error, "message")) {
    const message = error.message;
    if (Predicate.isString(message)) return message;
  }
  return String(error);
}

function promiseBoundary<A>(evaluate: () => Promise<A>): Effect.Effect<A, WorkbenchPromiseError> {
  return Effect.tryPromise({
    try: evaluate,
    catch: (cause) => WorkbenchPromiseError.make({ cause, message: errorMessage(cause) }),
  });
}

function base64FromArrayBuffer(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  const chunkSize = 0x8000;
  let binary = "";
  for (let offset = 0; offset < bytes.length; offset += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + chunkSize));
  }
  return globalThis.btoa(binary);
}

export class WorkbenchFiles extends Context.Service<
  WorkbenchFiles,
  {
    readonly readAsBase64: (file: File) => Effect.Effect<string, WorkbenchPromiseError>;
  }
>()("@trustgraph/workbench/atoms/workbench/WorkbenchFiles") {
  static readonly layer = Layer.succeed(
    WorkbenchFiles,
    WorkbenchFiles.of({
      readAsBase64: Effect.fn("WorkbenchFiles.readAsBase64")(function*(file: File) {
        return yield* promiseBoundary(() => file.arrayBuffer()).pipe(
          Effect.flatMap((buffer) =>
            Effect.try({
              try: () => base64FromArrayBuffer(buffer),
              catch: (cause) => WorkbenchPromiseError.make({ cause, message: errorMessage(cause) }),
            })
          ),
        );
      }),
    }),
  );
}

const workbenchBaseLayer = Layer.mergeAll(
  BrowserKeyValueStore.layerLocalStorage,
  BrowserClipboard.layer,
  WorkbenchFiles.layer,
  Layer.provide(browserObservabilityLayer, BrowserHttpClient.layerFetch),
);

export const workbenchRuntimeFactory = Atom.context({
  memoMap: Layer.makeMemoMapUnsafe(),
});

workbenchRuntimeFactory.addGlobalLayer(workbenchBaseLayer);

export const workbenchRuntime = workbenchRuntimeFactory(workbenchBaseLayer);

const queryCounter = Metric.counter("trustgraph_workbench_query_total", {
  description: "Workbench atom-backed query attempts",
});
const mutationCounter = Metric.counter("trustgraph_workbench_mutation_total", {
  description: "Workbench atom-backed mutation attempts",
});

// ---------------------------------------------------------------------------
// Shared types
// ---------------------------------------------------------------------------

export class FeatureSwitches extends S.Class<FeatureSwitches>("FeatureSwitches")({
  flowClasses: S.Boolean,
  submissions: S.Boolean,
  tokenCost: S.Boolean,
  schemas: S.Boolean,
  structuredQuery: S.Boolean,
  ontologyEditor: S.Boolean,
  agentTools: S.Boolean,
  mcpTools: S.Boolean,
  llmModels: S.Boolean,
}, { description: "Workbench feature visibility switches." }) {}

export class Settings extends S.Class<Settings>("Settings")({
  user: S.String,
  apiKey: S.String,
  collection: S.String,
  gatewayUrl: S.String,
  featureSwitches: FeatureSwitches,
}, { description: "Persisted workbench connection and display settings." }) {}

export type Theme = "dark" | "light";

export type ChatMode = "graph-rag" | "document-rag" | "agent";
export type MessageRole = "user" | "assistant" | "system";
export type AgentPhase = "think" | "observe" | "answer";

export class ChatMessage extends S.Class<ChatMessage>("ChatMessage")({
  id: S.String,
  role: S.Literals(["user", "assistant", "system"]),
  content: S.String,
  timestamp: S.Finite,
  isStreaming: S.optionalKey(S.Boolean),
  metadata: S.optionalKey(S.Struct({
    model: S.optionalKey(S.String),
    inTokens: S.optionalKey(S.Finite),
    outTokens: S.optionalKey(S.Finite),
  })),
  agentPhases: S.optionalKey(S.Struct({
    think: S.String,
    observe: S.String,
    answer: S.String,
  })),
  activePhase: S.optionalKey(S.Literals(["think", "observe", "answer"])),
  explainEvents: S.optionalKey(S.Array(ClientExplainEvent).pipe(S.mutable)),
}, { description: "A rendered chat transcript message." }) {}

export class ConversationState extends S.Class<ConversationState>("ConversationState")({
  messages: S.Array(ChatMessage).pipe(S.mutable),
  input: S.String,
  chatMode: S.Literals(["graph-rag", "document-rag", "agent"]),
}, { description: "Persisted workbench chat state." }) {}

export interface FlowSummary {
  id: string;
  description?: string;
  [key: string]: unknown;
}

export interface ProcessingMetadata {
  id: string;
  "document-id": string;
  flow: string;
  collection: string;
  [key: string]: unknown;
}

export class UploadProgress extends S.Class<UploadProgress>("UploadProgress")({
  phase: S.Literals(["preparing", "uploading", "finalizing"]),
  chunksTotal: S.Finite,
  chunksUploaded: S.Finite,
  bytesTotal: S.Finite,
  bytesUploaded: S.Finite,
}, { description: "Current chunked document upload progress." }) {}

export class UploadForm extends S.Class<UploadForm>("UploadForm")({
  file: S.NullOr(S.File),
  title: S.String,
  tags: S.String,
  comments: S.String,
  uploading: S.Boolean,
  dragOver: S.Boolean,
  progress: S.NullOr(UploadProgress),
}, { description: "Workbench document upload form state." }) {}

export class McpServerConfig extends S.Class<McpServerConfig>("McpServerConfig")({
  url: S.String,
  "remote-name": S.optionalKey(S.String),
  "auth-token": S.optionalKey(S.String),
}, { description: "Workbench MCP server config entry payload." }) {}

export class McpServerEntry extends S.Class<McpServerEntry>("McpServerEntry")({
  key: S.String,
  config: McpServerConfig,
}, { description: "Workbench MCP server config entry." }) {}

export class ToolArgument extends S.Class<ToolArgument>("ToolArgument")({
  name: S.String,
  type: S.String,
  description: S.String,
}, { description: "Workbench MCP tool argument descriptor." }) {}

export class ToolConfig extends S.Class<ToolConfig>("ToolConfig")({
  type: S.String,
  name: S.String,
  description: S.String,
  "mcp-tool": S.optionalKey(S.String),
  group: S.optionalKey(S.Array(S.String).pipe(S.mutable)),
  arguments: S.optionalKey(S.Array(ToolArgument).pipe(S.mutable)),
}, { description: "Workbench tool config entry payload." }) {}

export class ToolEntry extends S.Class<ToolEntry>("ToolEntry")({
  key: S.String,
  config: ToolConfig,
}, { description: "Workbench tool config entry." }) {}

export class TokenCost extends S.Class<TokenCost>("TokenCost")({
  model: S.String,
  input_price: S.Finite,
  output_price: S.Finite,
}, { description: "Model token pricing row." }) {}

export interface CollectionSummary {
  id?: string;
  collection?: string;
  name?: string;
  description?: string;
  tags?: string[];
  [key: string]: unknown;
}

export class Notification extends S.Class<Notification>("Notification")({
  id: S.String,
  type: S.Literals(["success", "error", "warning", "info"]),
  title: S.String,
  description: S.optionalKey(S.String),
}, { description: "Transient workbench notification toast." }) {}

export class McpServerForm extends S.Class<McpServerForm>("McpServerForm")({
  key: S.String,
  url: S.String,
  remoteName: S.String,
  authToken: S.String,
  showToken: S.Boolean,
  saving: S.Boolean,
  keyError: S.String,
}, { description: "Editable MCP server dialog state." }) {}

export class McpToolForm extends S.Class<McpToolForm>("McpToolForm")({
  key: S.String,
  name: S.String,
  description: S.String,
  mcpTool: S.String,
  group: S.String,
  args: S.Array(ToolArgument).pipe(S.mutable),
  saving: S.Boolean,
  keyError: S.String,
}, { description: "Editable MCP tool dialog state." }) {}

export class StartFlowForm extends S.Class<StartFlowForm>("StartFlowForm")({
  id: S.String,
  blueprint: S.String,
  description: S.String,
  paramsJson: S.String,
  submitting: S.Boolean,
  paramsError: S.NullOr(S.String),
  submitted: S.Boolean,
  definitionExpanded: S.Boolean,
}, { description: "Start-flow dialog form state." }) {}

export class CollectionForm extends S.Class<CollectionForm>("CollectionForm")({
  id: S.String,
  name: S.String,
  description: S.String,
  tags: S.String,
  submitting: S.Boolean,
}, { description: "Collection creation form state." }) {}

export class GraphViewState extends S.Class<GraphViewState>("GraphViewState")({
  searchTerm: S.String,
  selectedNodeId: S.NullOr(S.String),
  selectedNodeLabel: S.NullOr(S.String),
  showLabels: S.Boolean,
  showTypes: S.Boolean,
  nodeLimit: S.Finite,
}, { description: "Workbench graph display controls." }) {}

const DEFAULT_FEATURE_SWITCHES: FeatureSwitches = {
  flowClasses: false,
  submissions: false,
  tokenCost: false,
  schemas: false,
  structuredQuery: false,
  ontologyEditor: false,
  agentTools: false,
  mcpTools: false,
  llmModels: false,
};

export const DEFAULT_SETTINGS: Settings = {
  user: "default",
  apiKey: "",
  collection: "default",
  gatewayUrl: "",
  featureSwitches: DEFAULT_FEATURE_SWITCHES,
};

const ThemeSchema = S.Union([S.Literal("dark"), S.Literal("light")]);
const FlowIdSchema = S.String;

const DEFAULT_CONVERSATION: ConversationState = {
  messages: [],
  input: "",
  chatMode: "graph-rag",
};

const defaultUploadForm = (): UploadForm => ({
  file: null,
  title: "",
  tags: "",
  comments: "",
  uploading: false,
  dragOver: false,
  progress: null,
});

const defaultStartFlowForm = (): StartFlowForm => ({
  id: "",
  blueprint: "",
  description: "",
  paramsJson: "{}",
  submitting: false,
  paramsError: null,
  submitted: false,
  definitionExpanded: false,
});

const defaultCollectionForm = (): CollectionForm => ({
  id: "",
  name: "",
  description: "",
  tags: "",
  submitting: false,
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function legacySettings(): Settings {
  if (typeof localStorage === "undefined") return DEFAULT_SETTINGS;
  const raw = localStorage.getItem("trustgraph-settings");
  if (raw === null) return DEFAULT_SETTINGS;
  const parsed = parseJsonUnknown(raw) as { state?: { settings?: Partial<Settings> } } | undefined;
  if (parsed === undefined) return DEFAULT_SETTINGS;
  return {
    ...DEFAULT_SETTINGS,
    ...parsed.state?.settings,
    featureSwitches: {
      ...DEFAULT_FEATURE_SWITCHES,
      ...parsed.state?.settings?.featureSwitches,
    },
  };
}

function legacyConversation(): ConversationState {
  if (typeof localStorage === "undefined") return DEFAULT_CONVERSATION;
  const raw = localStorage.getItem("tg-conversation");
  if (raw === null) return DEFAULT_CONVERSATION;
  const parsed = parseJsonUnknown(raw) as { state?: Partial<ConversationState> } | undefined;
  if (parsed === undefined) return DEFAULT_CONVERSATION;
  const messages = (parsed.state?.messages ?? []).filter((message) => message.isStreaming !== true).slice(-200);
  return {
    ...DEFAULT_CONVERSATION,
    messages,
    chatMode: parsed.state?.chatMode ?? "graph-rag",
  };
}

function defaultTheme(): Theme {
  if (typeof localStorage !== "undefined") {
    const legacyTheme = localStorage.getItem("tg-theme");
    if (legacyTheme === "dark" || legacyTheme === "light") return legacyTheme;
  }
  if (typeof document !== "undefined" && document.documentElement.classList.contains("light")) {
    return "light";
  }
  return "dark";
}

function resultErrorMessage<A, E>(result: AsyncResult.AsyncResult<A, E>): string | null {
  if (result._tag !== "Failure") return null;
  return errorMessage(Cause.squash(result.cause));
}

const decodeJsonUnknown = S.decodeUnknownOption(S.UnknownFromJsonString);
const encodeJsonUnknown = S.encodeUnknownOption(S.fromJsonString(S.Unknown));

export function parseJsonUnknown(raw: string): unknown {
  return Option.getOrUndefined(decodeJsonUnknown(raw));
}

export function encodeJsonUnknownString(value: unknown): string {
  return Option.getOrElse(encodeJsonUnknown(value), () => "{}");
}

export function resultData<A, E>(result: AsyncResult.AsyncResult<A, E>, fallback: A): A {
  return AsyncResult.getOrElse(result, () => fallback);
}

export function resultLoading<A, E>(result: AsyncResult.AsyncResult<A, E>, value: unknown = null): boolean {
  if (result.waiting) return true;
  if (result._tag !== "Initial") return false;
  if (Array.isArray(value)) return value.length === 0;
  if (typeof value === "string") return value.length === 0;
  return value === null;
}

export function resultError<A, E>(result: AsyncResult.AsyncResult<A, E>): string | null {
  return resultErrorMessage(result);
}

const randomId = Effect.fn("trustgraph.workbench.randomId")(function*(prefix: string) {
  const left = yield* Random.nextIntBetween(0, 36 ** 6, { halfOpen: true });
  const right = yield* Random.nextIntBetween(0, 36 ** 6, { halfOpen: true });
  return `${prefix}-${left.toString(36).padStart(6, "0")}${right.toString(36).padStart(6, "0")}`;
});

function metadataFrom(metadata: StreamingMetadata | undefined): ChatMessage["metadata"] | undefined {
  if (metadata === undefined) return undefined;
  if (metadata.model === undefined && metadata.in_token === undefined && metadata.out_token === undefined) {
    return undefined;
  }
  return {
    ...(metadata.model !== undefined ? { model: metadata.model } : {}),
    ...(metadata.in_token !== undefined ? { inTokens: metadata.in_token } : {}),
    ...(metadata.out_token !== undefined ? { outTokens: metadata.out_token } : {}),
  };
}

function withoutActivePhase(message: ChatMessage): ChatMessage {
  const next = { ...message };
  delete next.activePhase;
  return next;
}

function mapConfigEntries(raw: unknown): Array<{ key: string; value: string }> {
  return Array.isArray(raw)
    ? raw
        .filter((item): item is { key: string; value: string } =>
          typeof item === "object" &&
          item !== null &&
          typeof (item as { key?: unknown }).key === "string" &&
          typeof (item as { value?: unknown }).value === "string",
        )
    : [];
}

function configValuesFromResponse(raw: unknown): Array<{ key: string; value: unknown; type?: string; workspace?: string }> {
  const values = jsonRecordProperty(raw, "values");
  if (!Array.isArray(values)) return [];
  return values.flatMap((value) => {
    if (!Predicate.isObject(value) || !Predicate.hasProperty(value, "key") || typeof value.key !== "string") {
      return [];
    }
    const entry: { key: string; value: unknown; type?: string; workspace?: string } = {
      key: value.key,
      value: Predicate.hasProperty(value, "value") ? value.value : undefined,
    };
    if (Predicate.hasProperty(value, "type") && typeof value.type === "string") entry.type = value.type;
    if (Predicate.hasProperty(value, "workspace") && typeof value.workspace === "string") entry.workspace = value.workspace;
    return [entry];
  });
}

function parseConfigValue(value: unknown): unknown {
  return typeof value === "string" ? parseJsonUnknown(value) ?? value : value;
}

function parseConfigEntries<T>(raw: unknown): T[] {
  const entries: T[] = [];
  for (const item of mapConfigEntries(raw)) {
    const config = parseJsonUnknown(item.value);
    if (config !== undefined) {
      entries.push({ key: item.key, config } as T);
    }
  }
  return entries;
}

function withDefaultCollection(collection: string): string {
  return collection.length > 0 ? collection : "default";
}

type WorkbenchReactivityKeys = ReadonlyArray<unknown> | Record<string, ReadonlyArray<unknown>>;
type WorkbenchRuntimeRequirements = BrowserClipboard.Clipboard | WorkbenchFiles | Reactivity.Reactivity;
type WorkbenchHttpAtomRequirements =
  | AtomRegistry.AtomRegistry
  | Reactivity.Reactivity
  | Scope.Scope
  | WorkbenchGatewayHttp;
type WorkbenchGatewayAtomRequirements =
  | AtomRegistry.AtomRegistry
  | Reactivity.Reactivity
  | Scope.Scope
  | WorkbenchGatewayHttp
  | WorkbenchGatewayRpc;
type WorkbenchDispatchInput = DispatchPayload;
type JsonRecord = Record<string, unknown>;

const StreamingEnvelopeSchema = S.Struct({
  response: S.optionalKey(S.Unknown),
  complete: S.optionalKey(S.Boolean),
  error: S.optionalKey(S.String),
});
type StreamingEnvelope = typeof StreamingEnvelopeSchema.Type;

const decodeStreamingEnvelope = S.decodeUnknownOption(StreamingEnvelopeSchema);
const decodeClientTriples = S.decodeUnknownOption(S.Array(ClientTriple).pipe(S.mutable));

function gatewayHttpBaseUrl(settings: Settings): string {
  const raw = settings.gatewayUrl.trim();
  if (raw.length === 0 || raw === "/api/v1/rpc") return "";
  if (raw.startsWith("/")) {
    return raw.replace(/\/api\/v1\/rpc$/, "").replace(/\/api\/v1$/, "");
  }
  const normalized = raw.startsWith("ws://")
    ? `http://${raw.slice("ws://".length)}`
    : raw.startsWith("wss://")
    ? `https://${raw.slice("wss://".length)}`
    : raw;
  const parsed = new URL(normalized);
  return parsed.origin;
}

function gatewayRpcUrl(settings: Settings): string {
  const raw = settings.gatewayUrl.trim().length > 0 ? settings.gatewayUrl.trim() : "/api/v1/rpc";
  const normalized = raw.startsWith("http://")
    ? `ws://${raw.slice("http://".length)}`
    : raw.startsWith("https://")
    ? `wss://${raw.slice("https://".length)}`
    : raw;
  if (settings.apiKey.length === 0) return normalized;
  const separator = normalized.includes("?") ? "&" : "?";
  return `${normalized}${separator}token=${encodeURIComponent(settings.apiKey)}`;
}

const gatewayHttpClientLayer = (get: Atom.AtomContext) => {
  const settings = get(settingsAtom);
  const baseUrl = gatewayHttpBaseUrl(settings);
  const token = settings.apiKey.length > 0 ? settings.apiKey : undefined;

  return Layer.effect(
    HttpClient.HttpClient,
    HttpClient.HttpClient.pipe(
      Effect.map((client) =>
        HttpClient.mapRequest(client, (request) => {
          const withBaseUrl = baseUrl.length > 0
            ? HttpClientRequest.prependUrl(request, baseUrl)
            : request;
          return token === undefined
            ? withBaseUrl
            : HttpClientRequest.bearerToken(withBaseUrl, token);
        })
      ),
    ),
  ).pipe(Layer.provide(BrowserHttpClient.layerFetch));
};

const gatewayRpcProtocolLayer = (get: Atom.AtomContext) => {
  const socketLayer = Layer.effect(
    Socket.Socket,
    Socket.makeWebSocket(gatewayRpcUrl(get(settingsAtom)), {
      closeCodeIsError: (code) => code !== 1000,
      openTimeout: "10 seconds",
    }),
  ).pipe(Layer.provide(Socket.layerWebSocketConstructorGlobal));

  return RpcClient.layerProtocolSocket({
    retryTransientErrors: true,
  }).pipe(
    Layer.provide(socketLayer),
    Layer.provide(RpcSerialization.layerNdjson),
  );
};

export class WorkbenchGatewayHttp extends AtomHttpApi.Service<WorkbenchGatewayHttp>()(
  "@trustgraph/workbench/atoms/workbench/WorkbenchGatewayHttp",
  {
    api: GatewayWorkbenchHttpApi,
    httpClient: gatewayHttpClientLayer,
    runtime: workbenchRuntimeFactory,
  },
) {}

export class WorkbenchGatewayRpc extends AtomRpc.Service<WorkbenchGatewayRpc>()(
  "@trustgraph/workbench/atoms/workbench/WorkbenchGatewayRpc",
  {
    group: TrustGraphRpcs,
    protocol: gatewayRpcProtocolLayer,
    runtime: workbenchRuntimeFactory,
  },
) {}

const workbenchGatewayRuntime = workbenchRuntimeFactory((get) =>
  Layer.merge(
    get(WorkbenchGatewayHttp.runtime.layer),
    get(WorkbenchGatewayRpc.runtime.layer),
  )
);

interface CommandOptions<A> {
  readonly initialValue?: A;
  readonly reactivityKeys?: WorkbenchReactivityKeys;
  readonly concurrent?: boolean;
}

function asJsonRecord(value: unknown): JsonRecord {
  return Predicate.isObject(value) && !Array.isArray(value) ? value as JsonRecord : {};
}

function jsonRecordProperty(value: unknown, key: string): unknown | undefined {
  return Predicate.isObject(value) && Predicate.hasProperty(value, key) ? value[key] : undefined;
}

function streamingEnvelopeFrom(message: unknown): StreamingEnvelope {
  return Option.getOrElse(decodeStreamingEnvelope(message), () => ({
    complete: true,
    error: "Streaming message could not be decoded",
  }));
}

function propertyValue(source: unknown, key: string): unknown | undefined {
  return Predicate.hasProperty(source, key) ? source[key] : undefined;
}

function stringProperty(source: unknown, key: string): string | undefined {
  const value = propertyValue(source, key);
  return typeof value === "string" ? value : undefined;
}

function numberProperty(source: unknown, key: string): number | undefined {
  const value = propertyValue(source, key);
  return typeof value === "number" ? value : undefined;
}

function booleanProperty(source: unknown, key: string): boolean | undefined {
  const value = propertyValue(source, key);
  return typeof value === "boolean" ? value : undefined;
}

function gatewayResponseErrorMessage(value: unknown): string | undefined {
  const error = jsonRecordProperty(value, "error");
  if (typeof error === "string") return error;
  const message = jsonRecordProperty(error, "message");
  return typeof message === "string" && message.length > 0 ? message : undefined;
}

function responseErrorMessage(source: unknown): string | undefined {
  const error = propertyValue(source, "error");
  if (typeof error === "string") return error;
  return stringProperty(error, "message");
}

function streamComplete(
  envelope: StreamingEnvelope,
  response: unknown,
  responseMarkers: ReadonlyArray<string> = [],
): boolean {
  return envelope.complete === true || responseMarkers.some((key) => booleanProperty(response, key) === true);
}

function explainTriplesFrom(source: unknown): Triple[] | undefined {
  return Option.getOrUndefined(decodeClientTriples(propertyValue(source, "explain_triples")));
}

function streamingMetadataFrom(source: unknown): StreamingMetadata | undefined {
  const metadata: {
    in_token?: number;
    out_token?: number;
    model?: string;
  } = {};
  let hasMetadata = false;

  const inToken = numberProperty(source, "in_token");
  if (inToken !== undefined) {
    metadata.in_token = inToken;
    hasMetadata = true;
  }
  const outToken = numberProperty(source, "out_token");
  if (outToken !== undefined) {
    metadata.out_token = outToken;
    hasMetadata = true;
  }
  const model = stringProperty(source, "model");
  if (model !== undefined) {
    metadata.model = model;
    hasMetadata = true;
  }

  return hasMetadata ? metadata : undefined;
}

function failWorkbenchRemote(operation: string, cause: unknown): WorkbenchPromiseError {
  return WorkbenchPromiseError.make({ cause, message: `${operation}: ${errorMessage(cause)}` });
}

function decodeResponseJsonEffect(value: unknown, operation: string): Effect.Effect<unknown, WorkbenchPromiseError> {
  const parsed = typeof value === "string" ? parseJsonUnknown(value) : value;
  return parsed === undefined
    ? Effect.fail(WorkbenchPromiseError.make({ cause: value, message: `${operation}: response JSON could not be decoded` }))
    : Effect.succeed(parsed);
}

function ensureNoGatewayResponseError<A>(operation: string, value: A): Effect.Effect<A, WorkbenchPromiseError> {
  const message = gatewayResponseErrorMessage(value);
  return message === undefined
    ? Effect.succeed(value)
    : Effect.fail(WorkbenchPromiseError.make({ cause: value, message: `${operation}: ${message}` }));
}

function qaBaseApi(): import("@trustgraph/client").BaseApi | undefined {
  if (typeof window === "undefined") return undefined;
  return (window as Window & { __TRUSTGRAPH_WORKBENCH_QA_API__?: import("@trustgraph/client").BaseApi }).__TRUSTGRAPH_WORKBENCH_QA_API__;
}

function makeWorkbenchGatewayApi(settings: Settings) {
  const user = settings.user;
  const dispatch = (
    service: string,
    request: JsonRecord,
    flow?: string,
  ): Effect.Effect<JsonRecord, WorkbenchPromiseError, WorkbenchGatewayHttp> =>
    Effect.gen(function* () {
      const qaApi = qaBaseApi();
      if (qaApi !== undefined) {
        const response = yield* promiseBoundary(() =>
          qaApi.makeRequest(service, request, undefined, undefined, flow)
        );
        return asJsonRecord(response);
      }

      const client = yield* WorkbenchGatewayHttp;
      const scope = flow === undefined ? "global" as const : "flow" as const;
      const input: WorkbenchDispatchInput = flow === undefined
        ? { scope, service, request }
        : { scope, service, flow, request };
      const response = yield* client.dispatch({ payload: DispatchPayload.make(input) });
      return asJsonRecord(response);
    }).pipe(
      Effect.mapError((cause) => failWorkbenchRemote(`dispatch ${service}`, cause)),
    );

  const flowDispatch = (flow: string, service: string, request: JsonRecord) =>
    dispatch(service, request, flow);

  const dispatchStream = (
    service: string,
    request: JsonRecord,
    flow: string,
    receive: (message: StreamingEnvelope) => boolean,
    label: string,
    onError: (message: string) => void,
  ): Effect.Effect<void, never, WorkbenchGatewayRpc> =>
    Effect.gen(function* () {
      const qaApi = qaBaseApi();
      if (qaApi !== undefined) {
        return yield* promiseBoundary(() =>
          qaApi.makeRequestMulti(
            service,
            request,
            (message) => receive(streamingEnvelopeFrom(message)),
            undefined,
            undefined,
            flow,
          )
        ).pipe(
          Effect.catch((cause) =>
            Effect.sync(() => {
              onError(`${label} request failed: ${errorMessage(cause)}`);
            })
          ),
          Effect.asVoid,
        );
      }

      const client = yield* WorkbenchGatewayRpc;
      const payload = DispatchPayload.make({
        scope: "flow",
        service,
        flow,
        request,
      });

      yield* client("DispatchStream", payload).pipe(
        Stream.runForEachWhile((chunk) =>
          Effect.sync(() => !receive({ response: chunk.response, complete: chunk.complete }))
        ),
      );
    }).pipe(
      Effect.catch((cause) =>
        Effect.sync(() => {
          onError(`${label} request failed: ${errorMessage(cause)}`);
        })
      ),
    );

  const configAll = () => dispatch("config", { operation: "config" }, undefined);

  const configApi = {
    getConfigAll: configAll,
    getPrompts: () =>
      configAll().pipe(
        Effect.map((response) => {
          const config = asJsonRecord(response.config);
          const promptNs = asJsonRecord(config.prompt);
          return Object.keys(promptNs)
            .filter((key) => key !== "system")
            .sort()
            .map((id) => ({ id, name: id }));
        }),
      ),
    getSystemPrompt: () =>
      configAll().pipe(
        Effect.map((response) => {
          const config = asJsonRecord(response.config);
          const prompt = asJsonRecord(config.prompt);
          const raw = prompt.system;
          return raw == null ? "" : raw;
        }),
      ),
    getPrompt: (id: string) =>
      configAll().pipe(
        Effect.map((response) => {
          const config = asJsonRecord(response.config);
          return asJsonRecord(config.prompt)[id] ?? null;
        }),
      ),
    getValues: (type: string) =>
      dispatch("config", { operation: "getvalues", type }, undefined).pipe(
        Effect.map((response) => configValuesFromResponse(response)),
      ),
    getTokenCosts: () =>
      dispatch("config", { operation: "getvalues", type: "token-cost" }, undefined).pipe(
        Effect.map((response) =>
          configValuesFromResponse(response).map((item) => {
            const value = parseConfigValue(item.value) as Record<string, number>;
            return {
              model: item.key,
              input_price: value.input_price,
              output_price: value.output_price,
            };
          })
        ),
      ),
    putConfig: (items: { type: string; key: string; value: string }[]) =>
      dispatch("config", { operation: "put", values: items }, undefined),
    deleteConfig: (target: { type: string; key: string }) =>
      dispatch("config", { operation: "delete", keys: [target] }, undefined),
  };

  return {
    user,
    flows: () => ({
      getFlows: () =>
        dispatch("flow", { operation: "list-flows" }, undefined).pipe(
          Effect.map((response) => Array.isArray(response["flow-ids"]) ? response["flow-ids"] as string[] : []),
        ),
      getFlow: (id: string) =>
        dispatch("flow", { operation: "get-flow", "flow-id": id }, undefined).pipe(
          Effect.flatMap((response) => decodeResponseJsonEffect(response.flow, "get-flow")),
        ),
      getFlowBlueprints: () =>
        dispatch("flow", { operation: "list-blueprints" }, undefined).pipe(
          Effect.map((response) => Array.isArray(response["blueprint-names"]) ? response["blueprint-names"] as string[] : []),
        ),
      getFlowBlueprint: (name: string) =>
        dispatch("flow", { operation: "get-blueprint", "blueprint-name": name }, undefined).pipe(
          Effect.flatMap((response) => decodeResponseJsonEffect(response["blueprint-definition"], "get-blueprint")),
        ),
      startFlow: (id: string, blueprint: string, description: string, parameters?: Record<string, unknown>) => {
        const request: JsonRecord = {
          operation: "start-flow",
          "flow-id": id,
          "blueprint-name": blueprint,
          description,
        };
        if (parameters !== undefined && Object.keys(parameters).length > 0) request.parameters = parameters;
        return dispatch("flow", request, undefined).pipe(
          Effect.flatMap((response) => ensureNoGatewayResponseError("start-flow", response)),
        );
      },
      stopFlow: (id: string) =>
        dispatch("flow", { operation: "stop-flow", "flow-id": id }, undefined),
    }),
    config: () => configApi,
    librarian: () => ({
      getDocuments: () =>
        dispatch("librarian", { operation: "list-documents", user }, undefined).pipe(
          Effect.map((response) => (response["document-metadatas"] ?? response.documents ?? []) as DocumentMetadata[]),
        ),
      getProcessing: () =>
        dispatch("librarian", { operation: "list-processing", user }, undefined).pipe(
          Effect.map((response) => (response["processing-metadatas"] ?? response.processing ?? response["processing-metadata"] ?? []) as ProcessingMetadata[]),
        ),
      getDocumentMetadata: (documentId: string) =>
        dispatch("librarian", {
          operation: "get-document-metadata",
          "document-id": documentId,
          documentId,
          user,
        }, undefined).pipe(
          Effect.map((response) => (response["document-metadata"] ?? response.documentMetadata ?? null) as DocumentMetadata | null),
        ),
      loadDocument: Effect.fn("trustgraph.workbench.gateway.librarian.loadDocument")(function*(
        document: string,
        mimeType: string,
        title: string,
        comments: string,
        tags: string[],
        id?: string,
        metadata?: Triple[],
      ) {
          const timestamp = yield* Clock.currentTimeMillis;
          const documentMetadata: DocumentMetadata = {
            time: Math.floor(timestamp / 1000),
            kind: mimeType,
            title,
            comments,
            user,
            tags,
            "document-type": "source",
            documentType: "source",
            ...(id !== undefined ? { id } : {}),
            ...(metadata !== undefined ? { metadata } : {}),
          };
          return yield* dispatch("librarian", {
            operation: "add-document",
            "document-metadata": documentMetadata,
            documentMetadata,
            content: document,
          }, undefined);
      }),
      removeDocument: (id: string, collection?: string) =>
        dispatch("librarian", {
          operation: "remove-document",
          "document-id": id,
          documentId: id,
          user,
          collection: withDefaultCollection(collection ?? "default"),
        }, undefined),
      beginUpload: (
        metadata: ChunkedUploadDocumentMetadata,
        totalSize: number,
        chunkSize?: number,
      ): Effect.Effect<BeginUploadResponse, WorkbenchPromiseError, WorkbenchGatewayHttp> => {
        const request: JsonRecord = {
          operation: "begin-upload",
          "document-metadata": metadata,
          documentMetadata: metadata,
          "total-size": totalSize,
        };
        if (chunkSize !== undefined) request["chunk-size"] = chunkSize;
        return dispatch("librarian", request, undefined).pipe(
          Effect.flatMap((response) => ensureNoGatewayResponseError("begin-upload", response)),
          Effect.map((response) => response as unknown as BeginUploadResponse),
        );
      },
      uploadChunk: (
        uploadId: string,
        chunkIndex: number,
        content: string,
      ): Effect.Effect<UploadChunkResponse, WorkbenchPromiseError, WorkbenchGatewayHttp> =>
        dispatch("librarian", {
          operation: "upload-chunk",
          "upload-id": uploadId,
          "chunk-index": chunkIndex,
          content,
          user,
        }, undefined).pipe(
          Effect.flatMap((response) => ensureNoGatewayResponseError("upload-chunk", response)),
          Effect.map((response) => response as unknown as UploadChunkResponse),
        ),
      completeUpload: (uploadId: string): Effect.Effect<CompleteUploadResponse, WorkbenchPromiseError, WorkbenchGatewayHttp> =>
        dispatch("librarian", {
          operation: "complete-upload",
          "upload-id": uploadId,
          user,
        }, undefined).pipe(
          Effect.flatMap((response) => ensureNoGatewayResponseError("complete-upload", response)),
          Effect.map((response) => response as unknown as CompleteUploadResponse),
        ),
    }),
    knowledge: () => ({
      getKnowledgeCores: () =>
        dispatch("knowledge", { operation: "list-kg-cores", user }, undefined).pipe(
          Effect.map((response) => Array.isArray(response.ids) ? response.ids as string[] : []),
        ),
      getDocumentEmbeddingCores: () =>
        dispatch("knowledge", { operation: "list-de-cores", user }, undefined).pipe(
          Effect.map((response) => Array.isArray(response.ids) ? response.ids as string[] : []),
        ),
      loadKgCore: (id: string, flow: string, collection?: string) =>
        dispatch("knowledge", {
          operation: "load-kg-core",
          id,
          flow,
          user,
          collection: withDefaultCollection(collection ?? "default"),
        }, undefined),
      deleteKgCore: (id: string, collection?: string) =>
        dispatch("knowledge", {
          operation: "delete-kg-core",
          id,
          user,
          collection: withDefaultCollection(collection ?? "default"),
        }, undefined),
    }),
    collectionManagement: () => ({
      listCollections: (tagFilter?: string[]) => {
        const request: JsonRecord = { operation: "list-collections", user };
        if (tagFilter !== undefined && tagFilter.length > 0) request.tag_filter = tagFilter;
        return dispatch("collection-management", request, undefined).pipe(
          Effect.map((response) => (response.collections ?? []) as CollectionSummary[]),
        );
      },
      updateCollection: (collection: string, name?: string, description?: string, tags?: string[]) => {
        const request: JsonRecord = { operation: "update-collection", user, collection };
        if (name !== undefined) request.name = name;
        if (description !== undefined) request.description = description;
        if (tags !== undefined) request.tags = tags;
        return dispatch("collection-management", request, undefined).pipe(
          Effect.flatMap((response) => {
            const collections = response.collections;
            return Array.isArray(collections) && collections.length > 0
              ? Effect.succeed(collections[0])
              : Effect.fail(WorkbenchPromiseError.make({ cause: response, message: "update-collection: failed to update collection" }));
          }),
        );
      },
      deleteCollection: (collection: string) =>
        dispatch("collection-management", {
          operation: "delete-collection",
          user,
          collection,
        }, undefined),
    }),
    flow: (flowId: string) => ({
      triplesQuery: Effect.fn("trustgraph.workbench.gateway.flow.triplesQuery")(function*(
        s?: Term,
        p?: Term,
        o?: Term,
        limit?: number,
        collection?: string,
        graph?: string,
      ) {
        const request: JsonRecord = {
          limit: limit ?? 20,
          user,
          collection: withDefaultCollection(collection ?? "default"),
        };
        if (s !== undefined) request.s = s;
        if (p !== undefined) request.p = p;
        if (o !== undefined) request.o = o;
        if (graph !== undefined) request.g = graph;
        return yield* flowDispatch(flowId, "triples", request).pipe(
          Effect.map((response) => (response.triples ?? response.response ?? []) as Triple[]),
        );
      }),
      graphRagStreaming: Effect.fn("trustgraph.workbench.gateway.flow.graphRagStreaming")(function*(
        text: string,
        receiver: (chunk: string, complete: boolean, metadata?: StreamingMetadata) => void,
        onError: (error: string) => void,
        options?: GraphRagOptions,
        collection?: string,
        onExplain?: (event: ExplainEvent) => void,
      ) {
        const recv = (message: unknown): boolean => {
          const msg = streamingEnvelopeFrom(message);
          if (msg.error !== undefined) {
            onError(msg.error);
            return true;
          }

          const resp = msg.response ?? {};
          const responseError = responseErrorMessage(resp);
          if (responseError !== undefined) {
            onError(responseError);
            return true;
          }

          const messageType = stringProperty(resp, "message_type");
          const explainId = stringProperty(resp, "explain_id");
          const explainTriples = explainTriplesFrom(resp);
          if (
            messageType === "explain" &&
            (explainId !== undefined || explainTriples !== undefined)
          ) {
            const event: ExplainEvent = {
              explainId: explainId ?? "",
              explainGraph: stringProperty(resp, "explain_graph") ?? "",
              ...(explainTriples !== undefined ? { explainTriples } : {}),
            };
            onExplain?.(event);
            if (
              stringProperty(resp, "response") === undefined &&
              booleanProperty(resp, "endOfStream") !== true &&
              booleanProperty(resp, "end_of_session") !== true
            ) {
              return false;
            }
          }

          const chunk = stringProperty(resp, "response") ?? stringProperty(resp, "chunk") ?? "";
          const complete = streamComplete(msg, resp, ["end_of_session", "endOfStream"]);
          const metadata = complete ? streamingMetadataFrom(resp) : undefined;
          receiver(chunk, complete, metadata);
          return complete;
        };

        const request: JsonRecord = {
          query: text,
          user,
          collection: withDefaultCollection(collection ?? "default"),
          streaming: true,
        };
        if (options?.entityLimit !== undefined) request["entity-limit"] = options.entityLimit;
        if (options?.tripleLimit !== undefined) request["triple-limit"] = options.tripleLimit;
        if (options?.maxSubgraphSize !== undefined) request["max-subgraph-size"] = options.maxSubgraphSize;
        if (options?.pathLength !== undefined) request["max-path-length"] = options.pathLength;

        return yield* dispatchStream("graph-rag", request, flowId, recv, "Graph RAG", onError);
      }),
      documentRagStreaming: Effect.fn("trustgraph.workbench.gateway.flow.documentRagStreaming")(function*(
        text: string,
        receiver: (chunk: string, complete: boolean, metadata?: StreamingMetadata) => void,
        onError: (error: string) => void,
        docLimit?: number,
        collection?: string,
        onExplain?: (event: ExplainEvent) => void,
      ) {
        const recv = (message: unknown): boolean => {
          const msg = streamingEnvelopeFrom(message);
          if (msg.error !== undefined) {
            onError(msg.error);
            return true;
          }

          const resp = msg.response ?? {};
          const responseError = responseErrorMessage(resp);
          if (responseError !== undefined) {
            onError(responseError);
            return true;
          }

          const explainId = stringProperty(resp, "explain_id");
          const explainGraph = stringProperty(resp, "explain_graph");
          if (
            stringProperty(resp, "message_type") === "explain" &&
            explainId !== undefined &&
            explainGraph !== undefined
          ) {
            onExplain?.({
              explainId,
              explainGraph,
            });
            return false;
          }

          const chunk = stringProperty(resp, "response") ?? stringProperty(resp, "chunk") ?? "";
          const complete = streamComplete(msg, resp, ["end_of_session", "endOfStream"]);
          const metadata = complete ? streamingMetadataFrom(resp) : undefined;
          receiver(chunk, complete, metadata);
          return complete;
        };

        const request: JsonRecord = {
          query: text,
          user,
          collection: withDefaultCollection(collection ?? "default"),
          streaming: true,
        };
        if (docLimit !== undefined) request["doc-limit"] = docLimit;

        return yield* dispatchStream("document-rag", request, flowId, recv, "Document RAG", onError);
      }),
      agent: Effect.fn("trustgraph.workbench.gateway.flow.agent")(function*(
        question: string,
        think: (chunk: string, complete: boolean, metadata?: StreamingMetadata) => void,
        observe: (chunk: string, complete: boolean, metadata?: StreamingMetadata) => void,
        answer: (chunk: string, complete: boolean, metadata?: StreamingMetadata) => void,
        error: (e: string) => void,
        onExplain?: (event: ExplainEvent) => void,
        collection?: string,
      ) {
        const recv = (message: unknown): boolean => {
          const msg = streamingEnvelopeFrom(message);
          if (msg.error !== undefined) {
            error(msg.error);
            return true;
          }

          const resp = msg.response ?? {};
          const responseError = responseErrorMessage(resp);
          if (stringProperty(resp, "chunk_type") === "error" || responseError !== undefined) {
            error(responseError ?? "Unknown agent error");
            return true;
          }

          const chunkType = stringProperty(resp, "chunk_type");
          const messageType = stringProperty(resp, "message_type");
          const explainId = stringProperty(resp, "explain_id");
          const explainTriples = explainTriplesFrom(resp);
          if (
            (chunkType === "explain" || messageType === "explain") &&
            (explainId !== undefined || explainTriples !== undefined)
          ) {
            const event: ExplainEvent = {
              explainId: explainId ?? "",
              explainGraph: stringProperty(resp, "explain_graph") ?? "",
              ...(explainTriples !== undefined ? { explainTriples } : {}),
            };
            onExplain?.(event);
            return false;
          }

          const content = stringProperty(resp, "content") ?? "";
          const messageComplete = booleanProperty(resp, "end_of_message") === true;
          const dialogComplete = streamComplete(msg, resp, ["end_of_dialog"]);
          const metadata = dialogComplete ? streamingMetadataFrom(resp) : undefined;

          Match.value(chunkType).pipe(
            Match.when("thought", () => think(content, messageComplete, metadata)),
            Match.when("observation", () => observe(content, messageComplete, metadata)),
            Match.when("answer", () => answer(content, messageComplete, metadata)),
            Match.when("final-answer", () => answer(content, messageComplete, metadata)),
            Match.when("action", () => undefined),
            Match.orElse(() => undefined),
          );

          return dialogComplete;
        };

        return yield* dispatchStream(
          "agent",
          {
            question,
            user,
            collection: withDefaultCollection(collection ?? "default"),
            streaming: true,
          },
          flowId,
          recv,
          "Agent",
          error,
        );
      }),
    }),
  };
}

type WorkbenchGatewayApi = ReturnType<typeof makeWorkbenchGatewayApi>;

function queryAtom<A>(
  name: string,
  fetcher: (get: Atom.AtomContext, api: WorkbenchGatewayApi) => Effect.Effect<A, WorkbenchError, WorkbenchGatewayHttp>,
  options?: {
    readonly reactivityKeys?: WorkbenchReactivityKeys;
  },
) {
  const readQuery = Effect.fn(`trustgraph.workbench.query.${name}`)(function*(get: Atom.AtomContext) {
    const api = makeWorkbenchGatewayApi(get(settingsAtom));
    return yield* fetcher(get, api).pipe(
      Effect.tap(() => Metric.update(queryCounter, 1)),
      Effect.tapError((error) => Effect.logError(`[workbench:${name}] query failed`, { error })),
    );
  });

  const atom = WorkbenchGatewayHttp.runtime.atom((get) => readQuery(get));
  const reactiveAtom = options?.reactivityKeys === undefined
    ? atom
    : workbenchRuntime.factory.withReactivity(options.reactivityKeys)(atom);

  return Atom.refreshOnWindowFocus(
    reactiveAtom,
  );
}

function localCommandAtom<Arg, A, R extends WorkbenchRuntimeRequirements = never>(
  name: string,
  run: (arg: Arg, get: Atom.FnContext) => Effect.Effect<A, WorkbenchError, R>,
  options?: CommandOptions<A>,
) {
  const runCommand = Effect.fn(`trustgraph.workbench.command.${name}`)(function*(arg: Arg, get: Atom.FnContext) {
    return yield* run(arg, get).pipe(
      Effect.tap(() => Metric.update(mutationCounter, 1)),
      Effect.tapError((error) => Effect.logError(`[workbench:${name}] command failed`, { error })),
    );
  });

  return workbenchRuntime.fn<Arg>()(runCommand, options);
}

function commandAtom<Arg, A, R extends WorkbenchRuntimeRequirements = never>(
  name: string,
  run: (arg: Arg, get: Atom.FnContext, api: WorkbenchGatewayApi) => Effect.Effect<A, WorkbenchError, R | WorkbenchGatewayHttp>,
  options?: CommandOptions<A>,
) {
  const runCommand = Effect.fn(`trustgraph.workbench.command.${name}`)(function*(arg: Arg, get: Atom.FnContext) {
    const api = makeWorkbenchGatewayApi(get(settingsAtom));
    return yield* run(arg, get, api).pipe(
      Effect.tap(() => Metric.update(mutationCounter, 1)),
      Effect.tapError((error) => Effect.logError(`[workbench:${name}] command failed`, { error })),
    );
  });

  // Browser-only services like WorkbenchFiles are installed as global layers on
  // workbenchRuntimeFactory, but AtomRuntime's type parameter only tracks the
  // HTTP service layer passed to AtomHttpApi.Service.
  return WorkbenchGatewayHttp.runtime.fn<Arg>()(
    runCommand as (
      arg: Arg,
      get: Atom.FnContext,
    ) => Effect.Effect<A, WorkbenchError, WorkbenchHttpAtomRequirements>,
    options,
  );
}

function gatewayCommandAtom<Arg, A, R extends WorkbenchRuntimeRequirements = never>(
  name: string,
  run: (arg: Arg, get: Atom.FnContext, api: WorkbenchGatewayApi) => Effect.Effect<A, WorkbenchError, R | WorkbenchGatewayHttp | WorkbenchGatewayRpc>,
  options?: CommandOptions<A>,
) {
  const runCommand = Effect.fn(`trustgraph.workbench.command.${name}`)(function*(arg: Arg, get: Atom.FnContext) {
    const api = makeWorkbenchGatewayApi(get(settingsAtom));
    return yield* run(arg, get, api).pipe(
      Effect.tap(() => Metric.update(mutationCounter, 1)),
      Effect.tapError((error) => Effect.logError(`[workbench:${name}] command failed`, { error })),
    );
  });

  return workbenchGatewayRuntime.fn<Arg>()(
    runCommand as (
      arg: Arg,
      get: Atom.FnContext,
    ) => Effect.Effect<A, WorkbenchError, WorkbenchGatewayAtomRequirements>,
    options,
  );
}

function setActivity(get: Atom.FnContext, label: string, active: boolean): void {
  const current = get(progressActivitiesAtom);
  const next = active
    ? [...current.filter((item) => item !== label), label]
    : current.filter((item) => item !== label);
  get.set(progressActivitiesAtom, next);
}

function updateConversation(get: Atom.FnContext, f: (current: ConversationState) => ConversationState): void {
  const current = get(conversationAtom) as ConversationState;
  const next = f(current);
  get.set(conversationAtom, {
    ...next,
    messages: next.messages.filter((message) => message.isStreaming !== true).length > 200
      ? next.messages.slice(-200)
      : next.messages,
  });
}

function updateLastMessage(get: Atom.FnContext, updater: (prev: ChatMessage) => ChatMessage): void {
  updateConversation(get, (current) =>
    A.matchRight(current.messages, {
      onEmpty: () => current,
      onNonEmpty: (init, last) => ({
        ...current,
        messages: [...init, updater(last)],
      }),
    }),
  );
}

function refreshConfigAtoms(get: Atom.FnContext): void {
  get.refresh(configAllAtom);
  get.refresh(promptsAtom);
  get.refresh(systemPromptAtom);
  get.refresh(mcpServersAtom);
  get.refresh(mcpToolsAtom);
  get.refresh(tokenCostsAtom);
}

function withActivity<A, R>(
  get: Atom.FnContext,
  label: string,
  effect: Effect.Effect<A, WorkbenchError, R>,
): Effect.Effect<A, WorkbenchError, R> {
  return Effect.sync(() => setActivity(get, label, true)).pipe(
    Effect.andThen(effect),
    Effect.ensuring(Effect.sync(() => setActivity(get, label, false))),
  );
}

// ---------------------------------------------------------------------------
// Local app state
// ---------------------------------------------------------------------------

export const settingsAtom = Atom.kvs({
  runtime: workbenchRuntime,
  key: "trustgraph-workbench-settings-v1",
  schema: S.toCodecJson(Settings),
  defaultValue: legacySettings,
}).pipe(Atom.keepAlive) as Atom.Writable<Settings, Settings>;

export const themeAtom = Atom.kvs({
  runtime: workbenchRuntime,
  key: "trustgraph-workbench-theme-v1",
  schema: S.toCodecJson(ThemeSchema),
  defaultValue: defaultTheme,
}).pipe(Atom.keepAlive) as Atom.Writable<Theme, Theme>;

export const flowIdAtom = Atom.kvs({
  runtime: workbenchRuntime,
  key: "trustgraph-workbench-flow-id-v1",
  schema: S.toCodecJson(FlowIdSchema),
  defaultValue: () => "default",
}).pipe(Atom.keepAlive) as Atom.Writable<string, string>;

export const conversationAtom = Atom.kvs({
  runtime: workbenchRuntime,
  key: "trustgraph-workbench-conversation-v1",
  schema: S.toCodecJson(ConversationState),
  defaultValue: legacyConversation,
}).pipe(Atom.keepAlive) as unknown as Atom.Writable<ConversationState, ConversationState>;

export const progressActivitiesAtom = Atom.make<string[]>([]).pipe(Atom.keepAlive);
export const isLoadingAtom = Atom.make((get) => get(progressActivitiesAtom).length > 0);

export const notificationsAtom = Atom.make<Notification[]>([]).pipe(Atom.keepAlive);

export const setSettingsFieldAtom = Atom.writable(
  () => null,
  (ctx, update: { key: keyof Settings; value: Settings[keyof Settings] }) => {
    ctx.set(settingsAtom, {
      ...ctx.get(settingsAtom),
      [update.key]: update.value,
    });
  },
);

export const updateFeatureSwitchesAtom = Atom.writable(
  () => null,
  (ctx, partial: Partial<FeatureSwitches>) => {
    const settings = ctx.get(settingsAtom);
    ctx.set(settingsAtom, {
      ...settings,
      featureSwitches: {
        ...settings.featureSwitches,
        ...partial,
      },
    });
  },
);

export const setConversationInputAtom = Atom.writable(
  () => null,
  (ctx, input: string) => {
    ctx.set(conversationAtom, { ...ctx.get(conversationAtom), input });
  },
);

export const setChatModeAtom = Atom.writable(
  () => null,
  (ctx, chatMode: ChatMode) => {
    ctx.set(conversationAtom, { ...ctx.get(conversationAtom), chatMode });
  },
);

export const deleteMessageAtom = Atom.writable(
  () => null,
  (ctx, id: string) => {
    const current = ctx.get(conversationAtom);
    ctx.set(conversationAtom, {
      ...current,
      messages: current.messages.filter((message) => message.id !== id),
    });
  },
);

export const clearMessagesAtom = Atom.writable(
  () => null,
  (ctx) => {
    ctx.set(conversationAtom, { ...ctx.get(conversationAtom), messages: [] });
  },
);

export const pushNotificationAtom = localCommandAtom<Omit<Notification, "id">, void>(
  "pushNotification",
  Effect.fn("trustgraph.workbench.pushNotification")(function*(input, get) {
    const id = yield* randomId("notif");
    const notification: Notification = { id, ...input };
    get.set(notificationsAtom, [...get(notificationsAtom), notification]);
    yield* Effect.sleep("5 seconds");
    get.set(notificationsAtom, get(notificationsAtom).filter((item) => item.id !== id));
  }),
  { concurrent: true },
);

export const removeNotificationAtom = Atom.writable(
  () => null,
  (ctx, id: string) => {
    ctx.set(notificationsAtom, ctx.get(notificationsAtom).filter((item) => item.id !== id));
  },
);

export const themeClassAtom = Atom.make((get) => {
  const theme = get(themeAtom);
  if (typeof document !== "undefined") {
    document.documentElement.classList.toggle("light", theme === "light");
    document.body.classList.toggle("light", theme === "light");
    document.body.classList.toggle("dark", theme === "dark");
  }
  return theme;
}).pipe(Atom.keepAlive);

export const toggleThemeAtom = Atom.writable(
  () => null,
  (ctx) => {
    ctx.set(themeAtom, ctx.get(themeAtom) === "dark" ? "light" : "dark");
  },
);

// ---------------------------------------------------------------------------
// Socket lifecycle
// ---------------------------------------------------------------------------

export const connectionStateAtom = Atom.make((get) => {
  const settings = get(settingsAtom);
  const hasApiKey = settings.apiKey.length > 0;
  const state: ConnectionState = {
    status: hasApiKey ? "authenticated" : "unauthenticated",
    hasApiKey,
  };
  return state;
}).pipe(Atom.keepAlive);

// ---------------------------------------------------------------------------
// Remote cached read atoms
// ---------------------------------------------------------------------------

export const flowsAtom = queryAtom(
  "flows",
  Effect.fn("trustgraph.workbench.flows")(function*(_get, api) {
    const ids = yield* api.flows().getFlows();
    return yield* Effect.all(
      ids.map((id) =>
        api.flows().getFlow(id).pipe(
          Effect.map((definition) => ({
            id,
            ...(typeof definition === "object" && definition !== null ? definition : {}),
          }) as FlowSummary),
        )
      ),
      { concurrency: 4 },
    );
  }),
  { reactivityKeys: ["flows"] },
).pipe(Atom.setIdleTTL("5 minutes"));

export const flowBlueprintsAtom = queryAtom(
  "flowBlueprints",
  Effect.fn("trustgraph.workbench.flowBlueprints")(function*(_get, api) {
    const list = yield* api.flows().getFlowBlueprints();
    return list ?? [];
  }),
  { reactivityKeys: ["flows", "flow-blueprints"] },
).pipe(Atom.setIdleTTL("10 minutes"));

export const flowBlueprintAtom = Atom.family((name: string) =>
  queryAtom(
    `flowBlueprint.${name}`,
    Effect.fn("trustgraph.workbench.flowBlueprint")(function*(_get, api) {
      if (name.length === 0) return null;
      return yield* api.flows().getFlowBlueprint(name);
    }),
    { reactivityKeys: ["flow-blueprint", name] },
  ).pipe(Atom.setIdleTTL("10 minutes")),
);

export const configAllAtom = queryAtom(
  "configAll",
  Effect.fn("trustgraph.workbench.configAll")(function*(_get, api) {
    return yield* api.config().getConfigAll();
  }),
  { reactivityKeys: ["config"] },
).pipe(Atom.setIdleTTL("2 minutes"));

export const promptsAtom = queryAtom(
  "prompts",
  Effect.fn("trustgraph.workbench.prompts")(function*(_get, api) {
    return yield* api.config().getPrompts();
  }),
  { reactivityKeys: ["config", "prompts"] },
).pipe(Atom.setIdleTTL("2 minutes"));

export const systemPromptAtom = queryAtom(
  "systemPrompt",
    Effect.fn("trustgraph.workbench.systemPrompt")(function*(_get, api) {
      const prompt = yield* api.config().getSystemPrompt();
      return typeof prompt === "string" ? prompt : encodeJsonUnknownString(prompt);
    }),
    { reactivityKeys: ["config", "system-prompt"] },
  ).pipe(Atom.setIdleTTL("2 minutes"));

export const promptDetailAtom = Atom.family((id: string) =>
  queryAtom(
    `prompt.${id}`,
    Effect.fn("trustgraph.workbench.promptDetail")(function*(_get, api) {
      if (id.length === 0) return null;
      return yield* api.config().getPrompt(id);
    }),
    { reactivityKeys: ["config", "prompt", id] },
  ).pipe(Atom.setIdleTTL("2 minutes")),
);

export const tokenCostsAtom = queryAtom(
  "tokenCosts",
  Effect.fn("trustgraph.workbench.tokenCosts")(function*(_get, api) {
    const data = yield* api.config().getTokenCosts();
    return Array.isArray(data)
      ? data.map((item: Record<string, unknown>) => ({
          model: String(item.model ?? ""),
          input_price: Number(item.input_price ?? 0),
          output_price: Number(item.output_price ?? 0),
        }))
      : [];
  }),
  { reactivityKeys: ["config", "token-costs"] },
).pipe(Atom.setIdleTTL("2 minutes"));

export const mcpServersAtom = queryAtom(
  "mcpServers",
  Effect.fn("trustgraph.workbench.mcpServers")(function*(_get, api) {
    const values = yield* api.config().getValues("mcp");
    return parseConfigEntries<McpServerEntry>(values);
  }),
  { reactivityKeys: ["config", "mcp"] },
).pipe(Atom.setIdleTTL("2 minutes"));

export const mcpToolsAtom = queryAtom(
  "mcpTools",
  Effect.fn("trustgraph.workbench.mcpTools")(function*(_get, api) {
    const values = yield* api.config().getValues("tool");
    return parseConfigEntries<ToolEntry>(values);
  }),
  { reactivityKeys: ["config", "tool"] },
).pipe(Atom.setIdleTTL("2 minutes"));

export const libraryDocumentsAtom = queryAtom(
  "libraryDocuments",
  Effect.fn("trustgraph.workbench.libraryDocuments")(function*(_get, api) {
    return yield* api.librarian().getDocuments();
  }),
  { reactivityKeys: ["library", "documents"] },
).pipe(Atom.setIdleTTL("1 minute"));

export const libraryProcessingAtom = queryAtom(
  "libraryProcessing",
  Effect.fn("trustgraph.workbench.libraryProcessing")(function*(_get, api) {
    return (yield* api.librarian().getProcessing()) as ProcessingMetadata[];
  }),
  { reactivityKeys: ["library", "processing"] },
).pipe(Atom.setIdleTTL("30 seconds"));

export const documentMetadataAtom = Atom.family((documentId: string) =>
  queryAtom(
    `documentMetadata.${documentId}`,
    Effect.fn("trustgraph.workbench.documentMetadata")(function*(_get, api) {
      if (documentId.length === 0) return null;
      return yield* api.librarian().getDocumentMetadata(documentId);
    }),
    { reactivityKeys: ["library", "document", documentId] },
  ).pipe(Atom.setIdleTTL("5 minutes")),
);

export const kgCoresAtom = queryAtom(
  "kgCores",
  Effect.fn("trustgraph.workbench.kgCores")(function*(_get, api) {
    return yield* api.knowledge().getKnowledgeCores();
  }),
  { reactivityKeys: ["knowledge", "kg-cores"] },
).pipe(Atom.setIdleTTL("2 minutes"));

export const deCoresAtom = queryAtom(
  "deCores",
  Effect.fn("trustgraph.workbench.deCores")(function*(_get, api) {
    return yield* api.knowledge().getDocumentEmbeddingCores();
  }),
  { reactivityKeys: ["knowledge", "de-cores"] },
).pipe(Atom.setIdleTTL("2 minutes"));

export const collectionsAtom = queryAtom(
  "collections",
  Effect.fn("trustgraph.workbench.collections")(function*(_get, api) {
    const collections = (yield* api.collectionManagement().listCollections()) as CollectionSummary[];
    const list = Array.isArray(collections) ? [...collections] : [];
    const hasDefault = list.some((item) => (item.collection ?? item.id ?? item.name) === "default");
    if (!hasDefault) list.unshift({ id: "default", collection: "default", name: "default" });
    return list;
  }),
  { reactivityKeys: ["collections"] },
).pipe(Atom.setIdleTTL("2 minutes"));

export class GraphTriplesInput extends S.Class<GraphTriplesInput>("GraphTriplesInput")({
  flowId: S.String,
  collection: S.String,
  limit: S.Finite,
}, { description: "Workbench graph triples query atom input." }) {}

export class ExplainTriplesInput extends S.Class<ExplainTriplesInput>("ExplainTriplesInput")({
  events: S.Array(ClientExplainEvent).pipe(S.mutable),
  flowId: S.String,
  collection: S.String,
}, { description: "Workbench explain triples query atom input." }) {}

const atomFamilyKeySeparator = "\u001f";
const explainGraphSeparator = "\u001e";
const explainTriplesInputs = MutableHashMap.empty<string, ExplainTriplesInput>();

function graphTriplesKey(input: GraphTriplesInput): string {
  return [input.flowId, input.collection, String(input.limit)].join(atomFamilyKeySeparator);
}

function parseGraphTriplesKey(key: string): GraphTriplesInput {
  const [flowId = "", collection = "", limit = "250"] = key.split(atomFamilyKeySeparator);
  const parsedLimit = Number(limit);
  return {
    flowId,
    collection,
    limit: Number.isFinite(parsedLimit) && parsedLimit > 0 ? parsedLimit : 250,
  };
}

function explainTriplesKey(input: ExplainTriplesInput): string {
  const graphs = input.events
    .map((event) => event.explainGraph ?? event.explainId ?? "")
    .filter((id) => id.length > 0)
    .sort()
    .join(explainGraphSeparator);
  return [input.flowId, input.collection, graphs].join(atomFamilyKeySeparator);
}

const graphTriplesAtomByKey = Atom.family((key: string) => {
  const input = parseGraphTriplesKey(key);
  return queryAtom(
    `graphTriples.${input.flowId}.${input.collection}.${input.limit}`,
    Effect.fn("trustgraph.workbench.graphTriples")(function*(_get, api) {
      return yield* (
        api.flow(input.flowId).triplesQuery(undefined, undefined, undefined, input.limit, input.collection)
      );
    }),
    { reactivityKeys: ["graph", input.flowId, input.collection] },
  ).pipe(Atom.setIdleTTL("1 minute"));
});

export const graphTriplesAtom = (input: GraphTriplesInput) => graphTriplesAtomByKey(graphTriplesKey(input));

const explainTriplesAtomByKey = Atom.family((key: string) =>
  queryAtom(
    `explainTriples.${key}`,
    Effect.fn("trustgraph.workbench.explainTriples")(function*(_get, api) {
      const input = Option.getOrUndefined(MutableHashMap.get(explainTriplesInputs, key));
      if (input === undefined) return [];
      const inlineTriples = input.events.flatMap((event): ReadonlyArray<Triple> => event.explainTriples ?? []);
      if (inlineTriples.length > 0) return [...inlineTriples];
      const graphUris = input.events.filter(
        (event): event is ExplainEvent & { explainGraph: string } =>
          event.explainGraph !== undefined && event.explainGraph.length > 0,
      );
      const results = yield* Effect.all(
        graphUris.map((event) =>
          (
            api.flow(input.flowId)
              .triplesQuery(undefined, undefined, undefined, 500, input.collection, event.explainGraph)
          ).pipe(Effect.orElseSucceed((): Array<Triple> => []))
        ),
        { concurrency: 4 },
      );
      return results.flat();
    }),
    {
      reactivityKeys: [
        "graph",
        key.split(atomFamilyKeySeparator)[0] ?? "",
        key.split(atomFamilyKeySeparator)[1] ?? "",
        "explain",
      ],
    },
  ).pipe(Atom.setIdleTTL("5 minutes")),
);

export const explainTriplesAtom = (input: ExplainTriplesInput) => {
  const key = explainTriplesKey(input);
  MutableHashMap.set(explainTriplesInputs, key, input);
  return explainTriplesAtomByKey(key);
};

// ---------------------------------------------------------------------------
// View-local atoms
// ---------------------------------------------------------------------------

export const uploadDialogOpenAtom = Atom.make(false).pipe(Atom.keepAlive);
export const uploadFormAtom = Atom.make<UploadForm>(defaultUploadForm()).pipe(Atom.keepAlive);
export const librarySearchAtom = Atom.make("").pipe(Atom.keepAlive);
export const libraryDeleteTargetAtom = Atom.make<DocumentMetadata | null>(null).pipe(Atom.keepAlive);
export const libraryDetailTargetAtom = Atom.make<DocumentMetadata | null>(null).pipe(Atom.keepAlive);

export const mcpActiveTabAtom = Atom.make<"servers" | "tools">("servers").pipe(Atom.keepAlive);
export const mcpServerDialogAtom = Atom.make<McpServerEntry | "new" | null>(null).pipe(Atom.keepAlive);
export const mcpToolDialogAtom = Atom.make<ToolEntry | "new" | null>(null).pipe(Atom.keepAlive);
export const mcpDeleteTargetAtom = Atom.make<{ type: "server" | "tool"; key: string } | null>(null).pipe(Atom.keepAlive);
export const mcpServerFormAtom = Atom.make<McpServerForm>({
  key: "",
  url: "",
  remoteName: "",
  authToken: "",
  showToken: false,
  saving: false,
  keyError: "",
}).pipe(Atom.keepAlive);
export const mcpToolFormAtom = Atom.make<McpToolForm>({
  key: "",
  name: "",
  description: "",
  mcpTool: "",
  group: "default",
  args: [],
  saving: false,
  keyError: "",
}).pipe(Atom.keepAlive);

export const knowledgeDeleteTargetAtom = Atom.make<string | null>(null).pipe(Atom.keepAlive);
export const activeActionAtom = Atom.make<string | null>(null).pipe(Atom.keepAlive);

export const flowsStartDialogOpenAtom = Atom.make(false).pipe(Atom.keepAlive);
export const startFlowFormAtom = Atom.make<StartFlowForm>(defaultStartFlowForm()).pipe(Atom.keepAlive);
export const flowExpandedAtom = Atom.make<Record<string, boolean>>({}).pipe(Atom.keepAlive);

export const settingsShowApiKeyAtom = Atom.make(false).pipe(Atom.keepAlive);
export const createCollectionDialogOpenAtom = Atom.make(false).pipe(Atom.keepAlive);
export const deleteCollectionDialogOpenAtom = Atom.make(false).pipe(Atom.keepAlive);
export const collectionFormAtom = Atom.make<CollectionForm>(defaultCollectionForm()).pipe(Atom.keepAlive);

export const promptActiveTabAtom = Atom.make<"templates" | "system">("templates").pipe(Atom.keepAlive);
export const selectedPromptIdAtom = Atom.make<string | null>(null).pipe(Atom.keepAlive);

export const graphViewAtom = Atom.make<GraphViewState>({
  searchTerm: "",
  selectedNodeId: null,
  selectedNodeLabel: null,
  showLabels: true,
  showTypes: true,
  nodeLimit: 250,
}).pipe(Atom.keepAlive);

export const agentPhaseExpandedAtom = Atom.make<Record<string, boolean>>({}).pipe(Atom.keepAlive);
export const copiedMessageIdAtom = Atom.make<string | null>(null).pipe(Atom.keepAlive);
export const activeChatRequestAtom = Atom.make<string | null>(null).pipe(Atom.keepAlive);

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

export const refreshWorkbenchAtom = commandAtom<"all" | "config" | "flows" | "library" | "knowledge", void, Reactivity.Reactivity>(
  "refreshWorkbench",
  Effect.fn("trustgraph.workbench.refreshWorkbench")(function*(target, get) {
    if (target === "all" || target === "flows") get.refresh(flowsAtom);
    if (target === "all" || target === "config") refreshConfigAtoms(get);
    if (target === "all" || target === "library") {
      get.refresh(libraryDocumentsAtom);
      get.refresh(libraryProcessingAtom);
    }
    if (target === "all" || target === "knowledge") {
      get.refresh(kgCoresAtom);
      get.refresh(deCoresAtom);
    }
    get.refresh(collectionsAtom);
    yield* Reactivity.invalidate([target]);
  }),
);

export const copyMessageAtom = localCommandAtom<
  { readonly id: string; readonly content: string },
  void,
  BrowserClipboard.Clipboard
>(
  "copyMessage",
  Effect.fn("trustgraph.workbench.copyMessage")(function*({ id, content }, get) {
    const clipboard = yield* BrowserClipboard.Clipboard;
    const copied = yield* clipboard.writeString(content).pipe(
      Effect.as(true),
      Effect.catch((error) =>
        Effect.sync(() => {
          get.set(pushNotificationAtom, {
            type: "error",
            title: "Copy failed",
            description: errorMessage(error),
          });
        }).pipe(Effect.as(false))
      ),
    );
    if (!copied) return;
    get.set(copiedMessageIdAtom, id);
    yield* Effect.sleep("2 seconds");
    if (get(copiedMessageIdAtom) === id) {
      get.set(copiedMessageIdAtom, null);
    }
  }),
  { concurrent: true },
);

export const startFlowAtom = commandAtom<
  { id: string; blueprint: string; description: string; parameters: Record<string, unknown> },
  void
>("startFlow", Effect.fn("trustgraph.workbench.startFlow")(function*(input, get, api) {
  yield* withActivity(
    get,
    `Start flow ${input.id}`,
    api.flows().startFlow(input.id, input.blueprint, input.description, input.parameters).pipe(
      Effect.tap(() => Effect.sync(() => {
        get.refresh(flowsAtom);
        get.set(flowIdAtom, input.id);
        get.set(pushNotificationAtom, {
          type: "success",
          title: "Flow started",
          description: `"${input.id}" is now active.`,
        });
      })),
    ),
  );
}), { reactivityKeys: ["flows"] });

export const stopFlowAtom = commandAtom<string, void>("stopFlow", Effect.fn("trustgraph.workbench.stopFlow")(function*(id, get, api) {
  yield* withActivity(
    get,
    `Stop flow ${id}`,
    api.flows().stopFlow(id).pipe(
      Effect.tap(() => Effect.sync(() => {
        get.refresh(flowsAtom);
        get.set(pushNotificationAtom, {
          type: "success",
          title: "Flow stopped",
          description: `"${id}" has been stopped.`,
        });
      })),
    ),
  );
}), { reactivityKeys: ["flows"] });

export const saveMcpServerAtom = commandAtom<{ key: string; config: McpServerConfig }, void>(
  "saveMcpServer",
  Effect.fn("trustgraph.workbench.saveMcpServer")(function*({ key, config }, get, api) {
    yield* api.config().putConfig([{ type: "mcp", key, value: encodeJsonUnknownString(config) }]);
    get.refresh(mcpServersAtom);
    get.refresh(configAllAtom);
    get.set(pushNotificationAtom, { type: "success", title: "MCP server saved", description: key });
  }),
  { reactivityKeys: ["config", "mcp"] },
);

export const deleteMcpServerAtom = commandAtom<string, void>("deleteMcpServer", Effect.fn("trustgraph.workbench.deleteMcpServer")(function*(key, get, api) {
  yield* api.config().deleteConfig({ type: "mcp", key });
  get.refresh(mcpServersAtom);
  get.refresh(configAllAtom);
  get.set(pushNotificationAtom, { type: "success", title: "MCP server deleted", description: key });
}), { reactivityKeys: ["config", "mcp"] });

export const saveMcpToolAtom = commandAtom<{ key: string; config: ToolConfig }, void>(
  "saveMcpTool",
  Effect.fn("trustgraph.workbench.saveMcpTool")(function*({ key, config }, get, api) {
    yield* api.config().putConfig([{ type: "tool", key, value: encodeJsonUnknownString(config) }]);
    get.refresh(mcpToolsAtom);
    get.refresh(configAllAtom);
    get.set(pushNotificationAtom, { type: "success", title: "Tool saved", description: key });
  }),
  { reactivityKeys: ["config", "tool"] },
);

export const deleteMcpToolAtom = commandAtom<string, void>("deleteMcpTool", Effect.fn("trustgraph.workbench.deleteMcpTool")(function*(key, get, api) {
  yield* api.config().deleteConfig({ type: "tool", key });
  get.refresh(mcpToolsAtom);
  get.refresh(configAllAtom);
  get.set(pushNotificationAtom, { type: "success", title: "Tool deleted", description: key });
}), { reactivityKeys: ["config", "tool"] });

const chunkedUploadThreshold = 1_000_000;

export class UploadDocumentInput extends S.Class<UploadDocumentInput>("UploadDocumentInput")({
  base64: S.String,
  mimeType: S.String,
  title: S.String,
  comments: S.String,
  tags: S.Array(S.String).pipe(S.mutable),
}, { description: "Workbench document upload command payload." }) {}

const uploadDocumentEffect = Effect.fn("trustgraph.workbench.uploadDocument.effect")(function*(
  input: UploadDocumentInput,
  get: Atom.FnContext,
  api: WorkbenchGatewayApi,
) {
  yield* withActivity(
    get,
    "Upload document",
    api.librarian().loadDocument(input.base64, input.mimeType, input.title, input.comments, input.tags).pipe(
      Effect.tap(() => Effect.sync(() => {
        get.refresh(libraryDocumentsAtom);
        get.refresh(libraryProcessingAtom);
        get.set(pushNotificationAtom, {
          type: "success",
          title: "Document uploaded",
          description: `"${input.title}" is being processed.`,
        });
      })),
    ),
  );
});

const uploadDocumentChunkedEffect = Effect.fn("trustgraph.workbench.uploadDocumentChunked.effect")(function*(
  input: UploadDocumentInput,
  get: Atom.FnContext,
  api: WorkbenchGatewayApi,
) {
  yield* withActivity(get, "Upload document (chunked)", Effect.gen(function*() {
    const totalSize = input.base64.length;
    get.set(uploadFormAtom, { ...get(uploadFormAtom), progress: {
      phase: "preparing",
      chunksTotal: 0,
      chunksUploaded: 0,
      bytesTotal: totalSize,
      bytesUploaded: 0,
    } });
    const lib = api.librarian();
    const documentId = yield* randomId("upload");
    const timestamp = yield* Clock.currentTimeMillis;
    const beginResp = yield* lib.beginUpload({
      id: documentId,
      time: Math.floor(timestamp / 1000),
      kind: input.mimeType,
      title: input.title,
      comments: input.comments,
      tags: input.tags,
      user: get(settingsAtom).user,
    }, totalSize);
    const uploadId = beginResp["upload-id"];
    const chunkSize = beginResp["chunk-size"];
    const totalChunks = beginResp["total-chunks"];
    let bytesUploaded = 0;
    for (let i = 0; i < totalChunks; i++) {
      const start = i * chunkSize;
      const end = Math.min(start + chunkSize, totalSize);
      const chunk = input.base64.slice(start, end);
      yield* lib.uploadChunk(uploadId, i, chunk);
      bytesUploaded += chunk.length;
      get.set(uploadFormAtom, { ...get(uploadFormAtom), progress: {
        phase: "uploading",
        chunksTotal: totalChunks,
        chunksUploaded: i + 1,
        bytesTotal: totalSize,
        bytesUploaded,
      } });
    }
    get.set(uploadFormAtom, { ...get(uploadFormAtom), progress: {
      phase: "finalizing",
      chunksTotal: totalChunks,
      chunksUploaded: totalChunks,
      bytesTotal: totalSize,
      bytesUploaded: totalSize,
    } });
    yield* lib.completeUpload(uploadId);
    get.refresh(libraryDocumentsAtom);
    get.refresh(libraryProcessingAtom);
    get.set(pushNotificationAtom, {
      type: "success",
      title: "Document uploaded",
      description: `"${input.title}" is being processed.`,
    });
  }));
});

export const uploadDocumentAtom = commandAtom<UploadDocumentInput, void>(
  "uploadDocument",
  Effect.fn("trustgraph.workbench.uploadDocument")(function*(input, get, api) {
    yield* uploadDocumentEffect(input, get, api);
  }),
  { reactivityKeys: ["library"] },
);

export const uploadDocumentChunkedAtom = commandAtom<UploadDocumentInput, void>(
  "uploadDocumentChunked",
  Effect.fn("trustgraph.workbench.uploadDocumentChunked")(function*(input, get, api) {
    yield* uploadDocumentChunkedEffect(input, get, api);
  }),
  { reactivityKeys: ["library"] },
);

export const submitUploadDocumentAtom = commandAtom<void, void, WorkbenchFiles>(
  "submitUploadDocument",
  Effect.fn("trustgraph.workbench.submitUploadDocument")(function*(_void, get, api) {
    const form = get(uploadFormAtom);
    if (form.file === null || form.uploading) return;
    const title = form.title.trim();
    if (title.length === 0) return;
    const file = form.file;
    get.set(uploadFormAtom, { ...form, uploading: true, progress: null });

    const submit = Effect.gen(function*() {
      const files = yield* WorkbenchFiles;
      const base64 = yield* files.readAsBase64(file);
      const input: UploadDocumentInput = {
        base64,
        mimeType: file.type.length > 0 ? file.type : "application/octet-stream",
        title,
        comments: form.comments,
        tags: form.tags.split(",").map((tag) => tag.trim()).filter((tag) => tag.length > 0),
      };
      if (base64.length > chunkedUploadThreshold) {
        yield* uploadDocumentChunkedEffect(input, get, api);
      } else {
        yield* uploadDocumentEffect(input, get, api);
      }
      get.set(uploadFormAtom, defaultUploadForm());
      get.set(uploadDialogOpenAtom, false);
    });

    yield* submit.pipe(
      Effect.tapError((error) =>
        Effect.sync(() => {
          get.set(uploadFormAtom, { ...get(uploadFormAtom), uploading: false, progress: null });
          get.set(pushNotificationAtom, {
            type: "error",
            title: "Upload failed",
            description: errorMessage(error),
          });
        })
      ),
    );
  }),
  { reactivityKeys: ["library"] },
);

export const removeDocumentAtom = commandAtom<string, void>("removeDocument", Effect.fn("trustgraph.workbench.removeDocument")(function*(documentId, get, api) {
  yield* withActivity(
    get,
    "Remove document",
    api.librarian().removeDocument(documentId, get(settingsAtom).collection).pipe(
      Effect.tap(() => Effect.sync(() => {
        get.refresh(libraryDocumentsAtom);
        get.refresh(libraryProcessingAtom);
        get.set(pushNotificationAtom, { type: "success", title: "Document deleted" });
      })),
    ),
  );
}), { reactivityKeys: ["library"] });

export const loadKgCoreAtom = commandAtom<string, void>("loadKgCore", Effect.fn("trustgraph.workbench.loadKgCore")(function*(id, get, api) {
  get.set(activeActionAtom, id);
  yield* api.knowledge().loadKgCore(id, get(flowIdAtom), get(settingsAtom).collection).pipe(
    Effect.tap(() => Effect.sync(() => {
      get.set(pushNotificationAtom, { type: "success", title: "Core loaded", description: id });
    })),
    Effect.ensuring(Effect.sync(() => get.set(activeActionAtom, null))),
  );
}), { reactivityKeys: ["knowledge"] });

export const deleteKgCoreAtom = commandAtom<string, void>("deleteKgCore", Effect.fn("trustgraph.workbench.deleteKgCore")(function*(id, get, api) {
  get.set(activeActionAtom, id);
  yield* api.knowledge().deleteKgCore(id, get(settingsAtom).collection).pipe(
    Effect.tap(() => Effect.sync(() => {
      get.refresh(kgCoresAtom);
      get.set(pushNotificationAtom, { type: "success", title: "Core deleted", description: id });
    })),
    Effect.ensuring(Effect.sync(() => get.set(activeActionAtom, null))),
  );
}), { reactivityKeys: ["knowledge"] });

export const createCollectionAtom = commandAtom<CollectionForm, void>("createCollection", Effect.fn("trustgraph.workbench.createCollection")(function*(form, get, api) {
  const id = form.id.trim();
  const tags = form.tags.split(",").map((tag) => tag.trim()).filter((tag) => tag.length > 0);
  yield* api.collectionManagement().updateCollection(
    id,
    form.name.trim().length > 0 ? form.name.trim() : undefined,
    form.description.trim().length > 0 ? form.description.trim() : undefined,
    tags.length > 0 ? tags : undefined,
  );
  get.refresh(collectionsAtom);
  get.set(pushNotificationAtom, {
    type: "success",
    title: "Collection created",
    description: `"${form.name.trim() || id}" is now active.`,
  });
}), { reactivityKeys: ["collections"] });

export const deleteCollectionAtom = commandAtom<string, void>("deleteCollection", Effect.fn("trustgraph.workbench.deleteCollection")(function*(id, get, api) {
  yield* api.collectionManagement().deleteCollection(id);
  get.refresh(collectionsAtom);
  const current = get(settingsAtom);
  if (current.collection === id) {
    get.set(settingsAtom, { ...current, collection: "default" });
  }
  get.set(pushNotificationAtom, { type: "success", title: "Collection deleted", description: id });
}), { reactivityKeys: ["collections"] });

export const submitMessageAtom = gatewayCommandAtom<{ input: string }, void>(
  "submitMessage",
  Effect.fn("trustgraph.workbench.submitMessage")(function*({ input }, get, api) {
  const trimmed = input.trim();
  if (trimmed.length === 0) return;

  const activityLabel = "Chat request";
  const flowId = get(flowIdAtom);
  const collection = withDefaultCollection(get(settingsAtom).collection);
  const chatMode = get(conversationAtom).chatMode;
  const flow = api.flow(flowId);
  const explainEvents: ExplainEvent[] = [];
  const requestId = yield* randomId("chat");
  const timestamp = yield* Clock.currentTimeMillis;
  const isActiveRequest = () => get(activeChatRequestAtom) === requestId;
  const finishRequest = () => {
    if (isActiveRequest()) {
      get.set(activeChatRequestAtom, null);
      setActivity(get, activityLabel, false);
    }
  };

  const userMsg: ChatMessage = {
    id: yield* randomId("msg"),
    role: "user",
    content: input,
    timestamp,
  };
  const assistantMsg: ChatMessage = {
    id: yield* randomId("msg"),
    role: "assistant",
    content: "",
    timestamp,
    isStreaming: true,
    ...(chatMode === "agent"
      ? {
          agentPhases: { think: "", observe: "", answer: "" },
          activePhase: "think" as const,
        }
      : {}),
  };

  updateConversation(get, (current) => ({
    ...current,
    input: "",
    messages: [...current.messages, userMsg, assistantMsg],
  }));
  get.set(activeChatRequestAtom, requestId);
  setActivity(get, activityLabel, true);

  const attachExplainEvents = () => {
    if (!isActiveRequest()) return;
    if (explainEvents.length > 0) {
      updateLastMessage(get, (previous) => ({ ...previous, explainEvents: [...explainEvents] }));
    }
  };

  const onError = (message: string) => {
    if (!isActiveRequest()) return;
    updateLastMessage(get, (previous) =>
      withoutActivePhase({
        ...previous,
        content: previous.content.length > 0 ? previous.content : `Error: ${message}`,
        isStreaming: false,
      }),
    );
    finishRequest();
  };

  const onChunk = (chunk: string, complete: boolean, metadata?: StreamingMetadata) => {
    if (!isActiveRequest()) return;
    updateLastMessage(get, (previous) => {
      const next: ChatMessage = {
        ...previous,
        content: previous.content + chunk,
        isStreaming: !complete,
      };
      const finalMetadata = complete ? metadataFrom(metadata) : undefined;
      return finalMetadata !== undefined ? { ...next, metadata: finalMetadata } : next;
    });
    if (complete) {
      attachExplainEvents();
      finishRequest();
    }
  };

  const onExplain = (event: ExplainEvent) => {
    if (!isActiveRequest()) return;
    explainEvents.push(event);
  };

  yield* Match.value(chatMode).pipe(
    Match.when("graph-rag", () =>
      flow.graphRagStreaming(trimmed, onChunk, onError, undefined, collection, onExplain)
    ),
    Match.when("document-rag", () =>
      flow.documentRagStreaming(trimmed, onChunk, onError, undefined, collection, onExplain)
    ),
    Match.when("agent", () =>
      flow.agent(
        trimmed,
        (chunk, complete) => {
          if (!isActiveRequest()) return;
          updateLastMessage(get, (previous) => {
            const phases = previous.agentPhases ?? { think: "", observe: "", answer: "" };
            return {
              ...previous,
              agentPhases: { ...phases, think: phases.think + chunk },
              ...(complete ? {} : { activePhase: "think" as const }),
            };
          });
        },
        (chunk, complete) => {
          if (!isActiveRequest()) return;
          updateLastMessage(get, (previous) => {
            const phases = previous.agentPhases ?? { think: "", observe: "", answer: "" };
            return {
              ...previous,
              agentPhases: { ...phases, observe: phases.observe + chunk },
              ...(complete ? {} : { activePhase: "observe" as const }),
            };
          });
        },
        (chunk, complete, metadata) => {
          if (!isActiveRequest()) return;
          updateLastMessage(get, (previous) => {
            const phases = previous.agentPhases ?? { think: "", observe: "", answer: "" };
            const answer = phases.answer + chunk;
            const next: ChatMessage = {
              ...previous,
              content: answer,
              agentPhases: { ...phases, answer },
              ...(complete ? {} : { activePhase: "answer" as const }),
              isStreaming: !complete,
            };
            const finalMetadata = complete ? metadataFrom(metadata) : undefined;
            const withMetadata = finalMetadata !== undefined ? { ...next, metadata: finalMetadata } : next;
            return complete ? withoutActivePhase(withMetadata) : withMetadata;
          });
          if (complete) {
            attachExplainEvents();
            finishRequest();
          }
        },
        onError,
        onExplain,
        collection,
      )
    ),
    Match.exhaustive,
  );
  }),
);

export const cancelChatAtom = Atom.writable(
  () => null,
  (ctx) => {
    const current = ctx.get(conversationAtom);
    const last = current.messages[current.messages.length - 1];
    if (last === undefined || last.role !== "assistant" || last.isStreaming !== true) return;
    ctx.set(conversationAtom, {
      ...current,
      messages: [
        ...current.messages.slice(0, -1),
        withoutActivePhase({
          ...last,
          content: last.content.length > 0 ? last.content : "(Cancelled)",
          isStreaming: false,
        }),
      ],
    });
    ctx.set(activeChatRequestAtom, null);
    ctx.set(progressActivitiesAtom, ctx.get(progressActivitiesAtom).filter((label) => label !== "Chat request"));
  },
);

export const regenerateLastMessageAtom = commandAtom<void, void>(
  "regenerateLastMessage",
  Effect.fn("trustgraph.workbench.regenerateLastMessage")((_void, get) => Effect.sync(() => {
    const current = get(conversationAtom);
    const lastUser = [...current.messages].reverse().find((message) => message.role === "user");
    if (lastUser === undefined) return;
    get.set(conversationAtom, {
      ...current,
      messages: current.messages.filter((message) => message.isStreaming !== true),
      input: lastUser.content,
    });
    get.set(activeChatRequestAtom, null);
    get.set(submitMessageAtom, { input: lastUser.content });
  })),
);

export function optionGet<A>(option: Option.Option<A>): A | undefined {
  return Option.getOrUndefined(option);
}

export type { AsyncResult, Term, Triple };
