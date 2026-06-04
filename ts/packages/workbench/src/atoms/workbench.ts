import { Clipboard as BrowserClipboard } from "@effect/platform-browser";
import * as BrowserHttpClient from "@effect/platform-browser/BrowserHttpClient";
import * as BrowserKeyValueStore from "@effect/platform-browser/BrowserKeyValueStore";
import { BaseApi, type ConnectionState, type DocumentMetadata, type ExplainEvent, type StreamingMetadata, type Term, type Triple } from "@trustgraph/client";
import { Cause, Clock, Context, Effect, Layer, Match, Metric, Option, Random, Schema as S } from "effect";
import * as Otlp from "effect/unstable/observability/Otlp";
import * as AsyncResult from "effect/unstable/reactivity/AsyncResult";
import * as Atom from "effect/unstable/reactivity/Atom";
import * as Reactivity from "effect/unstable/reactivity/Reactivity";

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

function errorMessage(error: unknown): string {
  if (isWorkbenchPromiseError(error)) return error.message;
  if (typeof error === "object" && error !== null && "message" in error) {
    const message = (error as { message?: unknown }).message;
    if (typeof message === "string") return message;
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

export const workbenchRuntime = workbenchRuntimeFactory(
  Layer.mergeAll(
    Reactivity.layer,
    workbenchBaseLayer,
  ),
);

const queryCounter = Metric.counter("trustgraph_workbench_query_total", {
  description: "Workbench atom-backed query attempts",
});
const mutationCounter = Metric.counter("trustgraph_workbench_mutation_total", {
  description: "Workbench atom-backed mutation attempts",
});

// ---------------------------------------------------------------------------
// Shared types
// ---------------------------------------------------------------------------

export interface FeatureSwitches {
  flowClasses: boolean;
  submissions: boolean;
  tokenCost: boolean;
  schemas: boolean;
  structuredQuery: boolean;
  ontologyEditor: boolean;
  agentTools: boolean;
  mcpTools: boolean;
  llmModels: boolean;
}

export interface Settings {
  user: string;
  apiKey: string;
  collection: string;
  gatewayUrl: string;
  featureSwitches: FeatureSwitches;
}

export interface WorkbenchApiFactory {
  readonly create: (settings: Settings) => BaseApi;
}

export type Theme = "dark" | "light";

export type ChatMode = "graph-rag" | "document-rag" | "agent";
export type MessageRole = "user" | "assistant" | "system";
export type AgentPhase = "think" | "observe" | "answer";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: number;
  isStreaming?: boolean;
  metadata?: {
    model?: string;
    inTokens?: number;
    outTokens?: number;
  };
  agentPhases?: {
    think: string;
    observe: string;
    answer: string;
  };
  activePhase?: AgentPhase;
  explainEvents?: ExplainEvent[];
}

export interface ConversationState {
  messages: ChatMessage[];
  input: string;
  chatMode: ChatMode;
}

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

export interface UploadProgress {
  phase: "preparing" | "uploading" | "finalizing";
  chunksTotal: number;
  chunksUploaded: number;
  bytesTotal: number;
  bytesUploaded: number;
}

export interface UploadForm {
  file: File | null;
  title: string;
  tags: string;
  comments: string;
  uploading: boolean;
  dragOver: boolean;
  progress: UploadProgress | null;
}

export interface McpServerConfig {
  url: string;
  "remote-name"?: string;
  "auth-token"?: string;
}

export interface McpServerEntry {
  key: string;
  config: McpServerConfig;
}

export interface ToolArgument {
  name: string;
  type: string;
  description: string;
}

export interface ToolConfig {
  type: string;
  name: string;
  description: string;
  "mcp-tool"?: string;
  group?: string[];
  arguments?: ToolArgument[];
}

export interface ToolEntry {
  key: string;
  config: ToolConfig;
}

export interface TokenCost {
  model: string;
  input_price: number;
  output_price: number;
}

export interface CollectionSummary {
  id?: string;
  collection?: string;
  name?: string;
  description?: string;
  tags?: string[];
  [key: string]: unknown;
}

export interface Notification {
  id: string;
  type: "success" | "error" | "warning" | "info";
  title: string;
  description?: string;
}

export interface McpServerForm {
  key: string;
  url: string;
  remoteName: string;
  authToken: string;
  showToken: boolean;
  saving: boolean;
  keyError: string;
}

export interface McpToolForm {
  key: string;
  name: string;
  description: string;
  mcpTool: string;
  group: string;
  args: ToolArgument[];
  saving: boolean;
  keyError: string;
}

export interface StartFlowForm {
  id: string;
  blueprint: string;
  description: string;
  paramsJson: string;
  submitting: boolean;
  paramsError: string | null;
  submitted: boolean;
  definitionExpanded: boolean;
}

export interface CollectionForm {
  id: string;
  name: string;
  description: string;
  tags: string;
  submitting: boolean;
}

export interface GraphViewState {
  searchTerm: string;
  selectedNodeId: string | null;
  selectedNodeLabel: string | null;
  showLabels: boolean;
  showTypes: boolean;
  nodeLimit: number;
}

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

const SettingsSchema = S.Struct({
  user: S.String,
  apiKey: S.String,
  collection: S.String,
  gatewayUrl: S.String,
  featureSwitches: S.Struct({
    flowClasses: S.Boolean,
    submissions: S.Boolean,
    tokenCost: S.Boolean,
    schemas: S.Boolean,
    structuredQuery: S.Boolean,
    ontologyEditor: S.Boolean,
    agentTools: S.Boolean,
    mcpTools: S.Boolean,
    llmModels: S.Boolean,
  }),
});

const ChatMessageSchema = S.Struct({
  id: S.String,
  role: S.Union([S.Literal("user"), S.Literal("assistant"), S.Literal("system")]),
  content: S.String,
  timestamp: S.Number,
  isStreaming: S.optionalKey(S.Boolean),
  metadata: S.optionalKey(S.Struct({
    model: S.optionalKey(S.String),
    inTokens: S.optionalKey(S.Number),
    outTokens: S.optionalKey(S.Number),
  })),
  agentPhases: S.optionalKey(S.Struct({
    think: S.String,
    observe: S.String,
    answer: S.String,
  })),
  activePhase: S.optionalKey(S.Union([S.Literal("think"), S.Literal("observe"), S.Literal("answer")])),
  explainEvents: S.optionalKey(S.Array(S.Unknown)),
});

const ConversationSchema = S.Struct({
  messages: S.Array(ChatMessageSchema),
  input: S.String,
  chatMode: S.Union([S.Literal("graph-rag"), S.Literal("document-rag"), S.Literal("agent")]),
});

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
  const result: NonNullable<ChatMessage["metadata"]> = {};
  if (metadata.model !== undefined) result.model = metadata.model;
  if (metadata.in_token !== undefined) result.inTokens = metadata.in_token;
  if (metadata.out_token !== undefined) result.outTokens = metadata.out_token;
  return Object.keys(result).length > 0 ? result : undefined;
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

function parseConfigEntries<T>(raw: unknown, label: string): T[] {
  const entries: T[] = [];
  for (const item of mapConfigEntries(raw)) {
    const config = parseJsonUnknown(item.value);
    if (config === undefined) {
      Effect.runSync(Effect.logWarning(`[workbench-atoms] Failed to parse ${label}: ${item.key}`));
    } else {
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

interface CommandOptions<A> {
  readonly initialValue?: A;
  readonly reactivityKeys?: WorkbenchReactivityKeys;
  readonly concurrent?: boolean;
}

function queryAtom<A>(
  name: string,
  fetcher: (get: Atom.AtomContext, api: BaseApi) => Effect.Effect<A, WorkbenchError>,
  options?: {
    readonly reactivityKeys?: WorkbenchReactivityKeys;
  },
) {
  const readQuery = Effect.fn(`trustgraph.workbench.query.${name}`)(function*(get: Atom.AtomContext) {
    const api = get(apiAtom);
    return yield* fetcher(get, api).pipe(
      Effect.tap(() => Metric.update(queryCounter, 1)),
      Effect.tapError((error) => Effect.logError(`[workbench:${name}] query failed`, { error })),
    );
  });

  const atom = workbenchRuntime.atom((get) => readQuery(get));
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
  run: (arg: Arg, get: Atom.FnContext, api: BaseApi) => Effect.Effect<A, WorkbenchError, R>,
  options?: CommandOptions<A>,
) {
  const runCommand = Effect.fn(`trustgraph.workbench.command.${name}`)(function*(arg: Arg, get: Atom.FnContext) {
    const api = get(apiAtom);
    return yield* run(arg, get, api).pipe(
      Effect.tap(() => Metric.update(mutationCounter, 1)),
      Effect.tapError((error) => Effect.logError(`[workbench:${name}] command failed`, { error })),
    );
  });

  return workbenchRuntime.fn<Arg>()(runCommand, options);
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
  updateConversation(get, (current) => {
    if (current.messages.length === 0) return current;
    const last = current.messages[current.messages.length - 1]!;
    return {
      ...current,
      messages: [...current.messages.slice(0, -1), updater(last)],
    };
  });
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
  schema: S.toCodecJson(SettingsSchema),
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
  schema: S.toCodecJson(ConversationSchema),
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

const liveApiFactory: WorkbenchApiFactory = {
  create: (settings) =>
    new BaseApi(
      settings.user,
      settings.apiKey.length > 0 ? settings.apiKey : undefined,
      settings.gatewayUrl.length > 0 ? settings.gatewayUrl : undefined,
    ),
};

export const apiFactoryAtom = Atom.make<WorkbenchApiFactory>(liveApiFactory).pipe(Atom.keepAlive);

export const apiAtom = Atom.make((get) => {
  const settings = get(settingsAtom);
  const api = get(apiFactoryAtom).create(settings);
  get.addFinalizer(() => api.close());
  return api;
}).pipe(Atom.keepAlive);

export const connectionStateAtom = Atom.make((get) => {
  const api = get(apiAtom);
  const fallback: ConnectionState = {
    status: "connecting",
    hasApiKey: get(settingsAtom).apiKey.length > 0,
  };
  const previous = Option.getOrElse(get.self<ConnectionState>(), () => fallback);
  const unsubscribe = api.onConnectionStateChange((state) => get.setSelf(state));
  get.addFinalizer(unsubscribe);
  return previous;
}).pipe(Atom.keepAlive);

// ---------------------------------------------------------------------------
// Remote cached read atoms
// ---------------------------------------------------------------------------

export const flowsAtom = queryAtom(
  "flows",
  Effect.fn("trustgraph.workbench.flows")(function*(_get, api) {
    const ids = yield* promiseBoundary(() => api.flows().getFlows());
    return yield* Effect.all(
      ids.map((id) =>
        promiseBoundary(() => api.flows().getFlow(id)).pipe(
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
    const list = yield* promiseBoundary(() => api.flows().getFlowBlueprints());
    return list ?? [];
  }),
  { reactivityKeys: ["flows", "flow-blueprints"] },
).pipe(Atom.setIdleTTL("10 minutes"));

export const flowBlueprintAtom = Atom.family((name: string) =>
  queryAtom(
    `flowBlueprint.${name}`,
    Effect.fn("trustgraph.workbench.flowBlueprint")(function*(_get, api) {
      if (name.length === 0) return null;
      return yield* promiseBoundary(() => api.flows().getFlowBlueprint(name));
    }),
    { reactivityKeys: ["flow-blueprint", name] },
  ).pipe(Atom.setIdleTTL("10 minutes")),
);

export const configAllAtom = queryAtom(
  "configAll",
  Effect.fn("trustgraph.workbench.configAll")(function*(_get, api) {
    return yield* promiseBoundary(() => api.config().getConfigAll());
  }),
  { reactivityKeys: ["config"] },
).pipe(Atom.setIdleTTL("2 minutes"));

export const promptsAtom = queryAtom(
  "prompts",
  Effect.fn("trustgraph.workbench.prompts")(function*(_get, api) {
    return yield* promiseBoundary(() => api.config().getPrompts());
  }),
  { reactivityKeys: ["config", "prompts"] },
).pipe(Atom.setIdleTTL("2 minutes"));

export const systemPromptAtom = queryAtom(
  "systemPrompt",
    Effect.fn("trustgraph.workbench.systemPrompt")(function*(_get, api) {
      const prompt = yield* promiseBoundary(() => api.config().getSystemPrompt());
      return typeof prompt === "string" ? prompt : encodeJsonUnknownString(prompt);
    }),
    { reactivityKeys: ["config", "system-prompt"] },
  ).pipe(Atom.setIdleTTL("2 minutes"));

export const promptDetailAtom = Atom.family((id: string) =>
  queryAtom(
    `prompt.${id}`,
    Effect.fn("trustgraph.workbench.promptDetail")(function*(_get, api) {
      if (id.length === 0) return null;
      return yield* promiseBoundary(() => api.config().getPrompt(id));
    }),
    { reactivityKeys: ["config", "prompt", id] },
  ).pipe(Atom.setIdleTTL("2 minutes")),
);

export const tokenCostsAtom = queryAtom(
  "tokenCosts",
  Effect.fn("trustgraph.workbench.tokenCosts")(function*(_get, api) {
    const data = yield* promiseBoundary(() => api.config().getTokenCosts());
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
    const values = yield* promiseBoundary(() => api.config().getValues("mcp"));
    return parseConfigEntries<McpServerEntry>(values, "MCP server config");
  }),
  { reactivityKeys: ["config", "mcp"] },
).pipe(Atom.setIdleTTL("2 minutes"));

export const mcpToolsAtom = queryAtom(
  "mcpTools",
  Effect.fn("trustgraph.workbench.mcpTools")(function*(_get, api) {
    const values = yield* promiseBoundary(() => api.config().getValues("tool"));
    return parseConfigEntries<ToolEntry>(values, "tool config");
  }),
  { reactivityKeys: ["config", "tool"] },
).pipe(Atom.setIdleTTL("2 minutes"));

export const libraryDocumentsAtom = queryAtom(
  "libraryDocuments",
  Effect.fn("trustgraph.workbench.libraryDocuments")(function*(_get, api) {
    return yield* promiseBoundary(() => api.librarian().getDocuments());
  }),
  { reactivityKeys: ["library", "documents"] },
).pipe(Atom.setIdleTTL("1 minute"));

export const libraryProcessingAtom = queryAtom(
  "libraryProcessing",
  Effect.fn("trustgraph.workbench.libraryProcessing")(function*(_get, api) {
    return (yield* promiseBoundary(() => api.librarian().getProcessing())) as ProcessingMetadata[];
  }),
  { reactivityKeys: ["library", "processing"] },
).pipe(Atom.setIdleTTL("30 seconds"));

export const documentMetadataAtom = Atom.family((documentId: string) =>
  queryAtom(
    `documentMetadata.${documentId}`,
    Effect.fn("trustgraph.workbench.documentMetadata")(function*(_get, api) {
      if (documentId.length === 0) return null;
      return yield* promiseBoundary(() => api.librarian().getDocumentMetadata(documentId));
    }),
    { reactivityKeys: ["library", "document", documentId] },
  ).pipe(Atom.setIdleTTL("5 minutes")),
);

export const kgCoresAtom = queryAtom(
  "kgCores",
  Effect.fn("trustgraph.workbench.kgCores")(function*(_get, api) {
    return yield* promiseBoundary(() => api.knowledge().getKnowledgeCores());
  }),
  { reactivityKeys: ["knowledge", "kg-cores"] },
).pipe(Atom.setIdleTTL("2 minutes"));

export const deCoresAtom = queryAtom(
  "deCores",
  Effect.fn("trustgraph.workbench.deCores")(function*(_get, api) {
    return yield* promiseBoundary(() => api.knowledge().getDocumentEmbeddingCores());
  }),
  { reactivityKeys: ["knowledge", "de-cores"] },
).pipe(Atom.setIdleTTL("2 minutes"));

export const collectionsAtom = queryAtom(
  "collections",
  Effect.fn("trustgraph.workbench.collections")(function*(_get, api) {
    const collections = (yield* promiseBoundary(() => api.collectionManagement().listCollections())) as CollectionSummary[];
    const list = Array.isArray(collections) ? [...collections] : [];
    const hasDefault = list.some((item) => (item.collection ?? item.id ?? item.name) === "default");
    if (!hasDefault) list.unshift({ id: "default", collection: "default", name: "default" });
    return list;
  }),
  { reactivityKeys: ["collections"] },
).pipe(Atom.setIdleTTL("2 minutes"));

export interface GraphTriplesInput {
  readonly flowId: string;
  readonly collection: string;
  readonly limit: number;
}

export interface ExplainTriplesInput {
  readonly events: ExplainEvent[];
  readonly flowId: string;
  readonly collection: string;
}

const atomFamilyKeySeparator = "\u001f";
const explainGraphSeparator = "\u001e";
const explainTriplesInputs = new Map<string, ExplainTriplesInput>();

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
      return yield* promiseBoundary(() =>
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
      const input = explainTriplesInputs.get(key);
      if (input === undefined) return [];
      const inlineTriples = input.events.flatMap((event) => event.explainTriples ?? []);
      if (inlineTriples.length > 0) return inlineTriples as Triple[];
      const graphUris = input.events.filter(
        (event): event is ExplainEvent & { explainGraph: string } =>
          event.explainGraph !== undefined && event.explainGraph.length > 0,
      );
      const results = yield* Effect.all(
        graphUris.map((event) =>
          promiseBoundary(() =>
            api.flow(input.flowId)
              .triplesQuery(undefined, undefined, undefined, 500, input.collection, event.explainGraph)
          ).pipe(Effect.orElseSucceed(() => [] as Triple[]))
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
  explainTriplesInputs.set(key, input);
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
    promiseBoundary(() => api.flows().startFlow(input.id, input.blueprint, input.description, input.parameters)).pipe(
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
    promiseBoundary(() => api.flows().stopFlow(id)).pipe(
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
    yield* promiseBoundary(() => api.config().putConfig([{ type: "mcp", key, value: encodeJsonUnknownString(config) }]));
    get.refresh(mcpServersAtom);
    get.refresh(configAllAtom);
    get.set(pushNotificationAtom, { type: "success", title: "MCP server saved", description: key });
  }),
  { reactivityKeys: ["config", "mcp"] },
);

export const deleteMcpServerAtom = commandAtom<string, void>("deleteMcpServer", Effect.fn("trustgraph.workbench.deleteMcpServer")(function*(key, get, api) {
  yield* promiseBoundary(() => api.config().deleteConfig({ type: "mcp", key }));
  get.refresh(mcpServersAtom);
  get.refresh(configAllAtom);
  get.set(pushNotificationAtom, { type: "success", title: "MCP server deleted", description: key });
}), { reactivityKeys: ["config", "mcp"] });

export const saveMcpToolAtom = commandAtom<{ key: string; config: ToolConfig }, void>(
  "saveMcpTool",
  Effect.fn("trustgraph.workbench.saveMcpTool")(function*({ key, config }, get, api) {
    yield* promiseBoundary(() => api.config().putConfig([{ type: "tool", key, value: encodeJsonUnknownString(config) }]));
    get.refresh(mcpToolsAtom);
    get.refresh(configAllAtom);
    get.set(pushNotificationAtom, { type: "success", title: "Tool saved", description: key });
  }),
  { reactivityKeys: ["config", "tool"] },
);

export const deleteMcpToolAtom = commandAtom<string, void>("deleteMcpTool", Effect.fn("trustgraph.workbench.deleteMcpTool")(function*(key, get, api) {
  yield* promiseBoundary(() => api.config().deleteConfig({ type: "tool", key }));
  get.refresh(mcpToolsAtom);
  get.refresh(configAllAtom);
  get.set(pushNotificationAtom, { type: "success", title: "Tool deleted", description: key });
}), { reactivityKeys: ["config", "tool"] });

const chunkedUploadThreshold = 1_000_000;

export interface UploadDocumentInput {
  readonly base64: string;
  readonly mimeType: string;
  readonly title: string;
  readonly comments: string;
  readonly tags: string[];
}

const uploadDocumentEffect = Effect.fn("trustgraph.workbench.uploadDocument.effect")(function*(
  input: UploadDocumentInput,
  get: Atom.FnContext,
  api: BaseApi,
) {
  yield* withActivity(
    get,
    "Upload document",
    promiseBoundary(() => api.librarian().loadDocument(input.base64, input.mimeType, input.title, input.comments, input.tags)).pipe(
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
  api: BaseApi,
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
    const beginResp = yield* promiseBoundary(() => lib.beginUpload({
      id: documentId,
      time: Math.floor(timestamp / 1000),
      kind: input.mimeType,
      title: input.title,
      comments: input.comments,
      tags: input.tags,
      user: get(settingsAtom).user,
    }, totalSize));
    const uploadId = beginResp["upload-id"];
    const chunkSize = beginResp["chunk-size"];
    const totalChunks = beginResp["total-chunks"];
    let bytesUploaded = 0;
    for (let i = 0; i < totalChunks; i++) {
      const start = i * chunkSize;
      const end = Math.min(start + chunkSize, totalSize);
      const chunk = input.base64.slice(start, end);
      yield* promiseBoundary(() => lib.uploadChunk(uploadId, i, chunk));
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
    yield* promiseBoundary(() => lib.completeUpload(uploadId));
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
    promiseBoundary(() => api.librarian().removeDocument(documentId, get(settingsAtom).collection)).pipe(
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
  yield* promiseBoundary(() => api.knowledge().loadKgCore(id, get(flowIdAtom), get(settingsAtom).collection)).pipe(
    Effect.tap(() => Effect.sync(() => {
      get.set(pushNotificationAtom, { type: "success", title: "Core loaded", description: id });
    })),
    Effect.ensuring(Effect.sync(() => get.set(activeActionAtom, null))),
  );
}), { reactivityKeys: ["knowledge"] });

export const deleteKgCoreAtom = commandAtom<string, void>("deleteKgCore", Effect.fn("trustgraph.workbench.deleteKgCore")(function*(id, get, api) {
  get.set(activeActionAtom, id);
  yield* promiseBoundary(() => api.knowledge().deleteKgCore(id, get(settingsAtom).collection)).pipe(
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
  yield* promiseBoundary(() => api.collectionManagement().updateCollection(
    id,
    form.name.trim().length > 0 ? form.name.trim() : undefined,
    form.description.trim().length > 0 ? form.description.trim() : undefined,
    tags.length > 0 ? tags : undefined,
  ));
  get.set(settingsAtom, { ...get(settingsAtom), collection: id });
  get.refresh(collectionsAtom);
  get.set(pushNotificationAtom, {
    type: "success",
    title: "Collection created",
    description: `"${form.name.trim() || id}" is now active.`,
  });
}), { reactivityKeys: ["collections"] });

export const deleteCollectionAtom = commandAtom<string, void>("deleteCollection", Effect.fn("trustgraph.workbench.deleteCollection")(function*(id, get, api) {
  yield* promiseBoundary(() => api.collectionManagement().deleteCollection(id));
  get.refresh(collectionsAtom);
  const current = get(settingsAtom);
  if (current.collection === id) {
    get.set(settingsAtom, { ...current, collection: "default" });
  }
  get.set(pushNotificationAtom, { type: "success", title: "Collection deleted", description: id });
}), { reactivityKeys: ["collections"] });

export const submitMessageAtom = commandAtom<{ input: string }, void>(
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

  Match.value(chatMode).pipe(
    Match.when("graph-rag", () => {
      flow.graphRagStreaming(trimmed, onChunk, onError, undefined, collection, onExplain);
    }),
    Match.when("document-rag", () => {
      flow.documentRagStreaming(trimmed, onChunk, onError, undefined, collection, onExplain);
    }),
    Match.when("agent", () => {
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
      );
    }),
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
