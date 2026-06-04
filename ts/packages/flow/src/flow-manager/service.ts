/**
 * Flow manager service -- manages flow lifecycle (start/stop/list) and blueprints.
 *
 * An AsyncProcessor (NOT FlowProcessor) that:
 * 1. Listens on flow-request topic
 * 2. Handles operations: list-flows, get-flow, start-flow, stop-flow,
 *    list-blueprints, get-blueprint, delete-blueprint
 * 3. Stores flows and blueprints in-memory
 * 4. On start/stop: pushes updated flow config to the config service
 *
 * Wire format uses kebab-case field names to match the client.
 * Access fields via bracket notation: request["flow-id"], response["flow-ids"].
 *
 * Python reference: trustgraph-flow/trustgraph/flow/service.py
 */

import {
  makeAsyncProcessor,
  type ProcessorConfig,
  type AsyncProcessorRuntime,
  type BackendConsumer,
  type BackendProducer,
  topics,
  makeRequestResponse,
  type RequestResponse,
  type ConfigRequest,
  type ConfigResponse,
  FlowRequest as FlowRequestSchema,
  FlowResponse as FlowResponseSchema,
  type FlowRequest,
  type FlowResponse,
  errorMessage,
} from "@trustgraph/base";
import { makeProcessorProgram } from "@trustgraph/base";
import type { Message } from "@trustgraph/base";
import { NodeRuntime } from "@effect/platform-node";
import { Duration, Effect, Layer, ManagedRuntime, Match, Option, SynchronizedRef } from "effect";
import * as S from "effect/Schema";

// ---------- Internal state types ----------

interface FlowInstance {
  id: string;
  blueprintName: string;
  description: string;
  parameters: Record<string, unknown>;
  status: "running" | "stopped";
}

interface Blueprint {
  description: string;
  topics: Record<string, string>;
  parameters?: Record<string, unknown>;
  [key: string]: unknown;
}

interface ConfigValueEntry {
  key: string;
  value: unknown;
}

export class FlowManagerError extends S.TaggedErrorClass<FlowManagerError>()(
  "FlowManagerError",
  {
    message: S.String,
    operation: S.String,
  },
) {}

const flowManagerError = (operation: string, cause: unknown): FlowManagerError =>
  FlowManagerError.make({
    operation,
    message: errorMessage(cause),
  });

const decodeJsonUnknown = S.decodeUnknownOption(S.UnknownFromJsonString);

const encodeJson = (value: unknown, operation: string): Effect.Effect<string, FlowManagerError> =>
  S.encodeUnknownEffect(S.UnknownFromJsonString)(value).pipe(
    Effect.mapError((cause) => flowManagerError(operation, cause)),
  );

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function optionalString(value: unknown): string | undefined {
  return typeof value === "string" && value.length > 0 ? value : undefined;
}

function configValues(response: ConfigResponse): ConfigValueEntry[] {
  const values = response.values;
  if (!Array.isArray(values)) return [];
  return values.flatMap((value) => {
    if (!isRecord(value)) return [];
    const key = optionalString(value.key);
    if (key === undefined) return [];
    return [{ key, value: value.value }];
  });
}

function parseConfigRecord(value: unknown): Record<string, unknown> | undefined {
  const parsed = typeof value === "string"
    ? Option.getOrUndefined(decodeJsonUnknown(value))
    : value;
  return isRecord(parsed) ? parsed : undefined;
}

// ---------- Default blueprint ----------

const DEFAULT_BLUEPRINT: Blueprint = {
  description: "Default processing pipeline with all services",
  topics: {
    // Document processing pipeline
    "decode-input": "tg.flow.document",
    "decode-output": "tg.flow.text-document",
    "decode-triples": "tg.flow.triples",
    "chunk-input": "tg.flow.text-document",
    "chunk-output": "tg.flow.chunk",
    "chunk-triples": "tg.flow.triples",
    "extract-input": "tg.flow.chunk",
    "extract-triples": "tg.flow.triples",
    "extract-entity-contexts": "tg.flow.entity-contexts",
    // Storage consumers
    "store-triples-input": "tg.flow.triples",
    "store-graph-embeddings-input": "tg.flow.entity-contexts",
    // LLM text completion
    "text-completion-request": "tg.flow.text-completion-request",
    "text-completion-response": "tg.flow.text-completion-response",
    // Prompt service
    "prompt-request": "tg.flow.prompt-request",
    "prompt-response": "tg.flow.prompt-response",
    // Graph RAG
    "graph-rag-request": "tg.flow.graph-rag-request",
    "graph-rag-response": "tg.flow.graph-rag-response",
    // Document RAG
    "document-rag-request": "tg.flow.document-rag-request",
    "document-rag-response": "tg.flow.document-rag-response",
    // Triples query
    "triples-request": "tg.flow.triples-request",
    "triples-response": "tg.flow.triples-response",
    // Agent
    "agent-request": "tg.flow.agent-request",
    "agent-response": "tg.flow.agent-response",
    // Embeddings
    "embeddings-request": "tg.flow.embeddings-request",
    "embeddings-response": "tg.flow.embeddings-response",
    // Graph embeddings query
    "graph-embeddings-request": "tg.flow.graph-embeddings-request",
    "graph-embeddings-response": "tg.flow.graph-embeddings-response",
    // Document embeddings query
    "document-embeddings-request": "tg.flow.document-embeddings-request",
    "document-embeddings-response": "tg.flow.document-embeddings-response",
    // Librarian RPC (for PDF decoder)
    "librarian-request": "tg.flow.librarian-request",
    "librarian-response": "tg.flow.librarian-response",
    // MCP tool invocation
    "mcp-tool-request": "tg.flow.mcp-tool-request",
    "mcp-tool-response": "tg.flow.mcp-tool-response",
  },
};

// ---------- Service ----------

interface FlowManagerServiceState {
  readonly flows: Map<string, FlowInstance>;
  readonly blueprints: Map<string, Blueprint>;
  readonly consumer: BackendConsumer<FlowRequest> | null;
  readonly responseProducer: BackendProducer<FlowResponse> | null;
  readonly configClient: RequestResponse<ConfigRequest, ConfigResponse> | null;
}

export interface FlowManagerService extends AsyncProcessorRuntime<FlowManagerError> {
  readonly state: SynchronizedRef.SynchronizedRef<FlowManagerServiceState>;
  readonly handleMessage: (msg: Message<FlowRequest>) => Promise<void>;
  readonly handleMessageEffect: (msg: Message<FlowRequest>) => Effect.Effect<void, FlowManagerError>;
  readonly configRequest: (request: ConfigRequest) => Promise<ConfigResponse>;
  readonly configRequestEffect: (request: ConfigRequest) => Effect.Effect<ConfigResponse, FlowManagerError>;
  readonly ensureDefaultBlueprint: () => Promise<void>;
  readonly ensureDefaultBlueprintEffect: Effect.Effect<void, FlowManagerError>;
  readonly refreshBlueprintsFromConfig: () => Promise<void>;
  readonly refreshBlueprintsFromConfigEffect: Effect.Effect<void, FlowManagerError>;
  readonly refreshFlowsFromConfig: () => Promise<void>;
  readonly refreshFlowsFromConfigEffect: Effect.Effect<void, FlowManagerError>;
  readonly handleOperation: (request: FlowRequest) => Promise<FlowResponse>;
  readonly handleOperationEffect: (request: FlowRequest) => Effect.Effect<FlowResponse, FlowManagerError>;
  readonly handleListBlueprints: () => FlowResponse;
  readonly handleGetBlueprint: (request: FlowRequest) => Promise<FlowResponse>;
  readonly handleGetBlueprintEffect: (request: FlowRequest) => Effect.Effect<FlowResponse, FlowManagerError>;
  readonly handlePutBlueprint: (request: FlowRequest) => Promise<FlowResponse>;
  readonly handlePutBlueprintEffect: (request: FlowRequest) => Effect.Effect<FlowResponse, FlowManagerError>;
  readonly handleDeleteBlueprint: (request: FlowRequest) => Promise<FlowResponse>;
  readonly handleDeleteBlueprintEffect: (request: FlowRequest) => Effect.Effect<FlowResponse, FlowManagerError>;
  readonly handleListFlows: () => FlowResponse;
  readonly handleGetFlow: (request: FlowRequest) => Promise<FlowResponse>;
  readonly handleGetFlowEffect: (request: FlowRequest) => Effect.Effect<FlowResponse, FlowManagerError>;
  readonly handleStartFlow: (request: FlowRequest) => Promise<FlowResponse>;
  readonly handleStartFlowEffect: (request: FlowRequest) => Effect.Effect<FlowResponse, FlowManagerError>;
  readonly handleStopFlow: (request: FlowRequest) => Promise<FlowResponse>;
  readonly handleStopFlowEffect: (request: FlowRequest) => Effect.Effect<FlowResponse, FlowManagerError>;
  readonly pushFlowsConfig: () => Promise<void>;
  readonly pushFlowsConfigEffect: Effect.Effect<void>;
  readonly deleteFlowConfig: (id: string) => Promise<void>;
  readonly deleteFlowConfigEffect: (id: string) => Effect.Effect<void, FlowManagerError>;
}

const initialState = (): FlowManagerServiceState => {
  const blueprints = new Map<string, Blueprint>();
  blueprints.set("default", DEFAULT_BLUEPRINT);
  return {
    flows: new Map<string, FlowInstance>(),
    blueprints,
    consumer: null,
    responseProducer: null,
    configClient: null,
  };
};

const isStringRecord = (value: unknown): value is Record<string, string> =>
  isRecord(value) && Object.values(value).every((item) => typeof item === "string");

const cloneFlows = (source: Map<string, FlowInstance>): Map<string, FlowInstance> =>
  new Map(source);

const cloneBlueprints = (source: Map<string, Blueprint>): Map<string, Blueprint> =>
  new Map(source);

const stateSnapshot = (
  stateRef: SynchronizedRef.SynchronizedRef<FlowManagerServiceState>,
): FlowManagerServiceState =>
  SynchronizedRef.getUnsafe(stateRef);

const modifyResult = <Value>(
  value: Value,
  state: FlowManagerServiceState,
): readonly [Value, FlowManagerServiceState] => [value, state];

function blueprintFromConfig(value: unknown): Blueprint | undefined {
  const parsed = parseConfigRecord(value);
  if (parsed === undefined) return undefined;
  const topics = isStringRecord(parsed.topics) ? parsed.topics : undefined;
  if (topics === undefined) return undefined;
  const parameters = isRecord(parsed.parameters) ? parsed.parameters : undefined;
  return {
    ...parsed,
    description: optionalString(parsed.description) ?? "",
    topics,
    ...(parameters === undefined ? {} : { parameters }),
  } satisfies Blueprint;
}

function flowFromConfig(id: string, value: unknown): FlowInstance | undefined {
  const parsed = parseConfigRecord(value);
  if (parsed === undefined) return undefined;
  return {
    id,
    blueprintName: optionalString(parsed["blueprint-name"]) ?? optionalString(parsed.blueprintName) ?? "default",
    description: optionalString(parsed.description) ?? "",
    parameters: isRecord(parsed.parameters) ? parsed.parameters : {},
    status: "running",
  };
}

const updateHandles = (
  stateRef: SynchronizedRef.SynchronizedRef<FlowManagerServiceState>,
  handles: {
    readonly consumer?: BackendConsumer<FlowRequest> | null;
    readonly responseProducer?: BackendProducer<FlowResponse> | null;
    readonly configClient?: RequestResponse<ConfigRequest, ConfigResponse> | null;
  },
) =>
  SynchronizedRef.updateAndGet(stateRef, (state) => ({
    ...state,
    consumer: handles.consumer === undefined ? state.consumer : handles.consumer,
    responseProducer: handles.responseProducer === undefined ? state.responseProducer : handles.responseProducer,
    configClient: handles.configClient === undefined ? state.configClient : handles.configClient,
  }));

const configRequestEffect = Effect.fn("FlowManager.configRequest")(function* (
  stateRef: SynchronizedRef.SynchronizedRef<FlowManagerServiceState>,
  request: ConfigRequest,
) {
  const configClient = (yield* SynchronizedRef.get(stateRef)).configClient;
  if (configClient === null) {
    return yield* flowManagerError("config-request", "Config client not started");
  }
  return yield* Effect.tryPromise({
    try: () => configClient.request(request),
    catch: (cause) => flowManagerError("config-request", cause),
  });
});

const ensureDefaultBlueprintEffect = Effect.fn("FlowManager.ensureDefaultBlueprint")(function* (
  stateRef: SynchronizedRef.SynchronizedRef<FlowManagerServiceState>,
) {
  const response = yield* configRequestEffect(stateRef, {
    operation: "getvalues",
    type: "flow-blueprint",
  });
  if (configValues(response).some((value) => value.key === "default")) {
    return;
  }

  const defaultBlueprint = yield* encodeJson(DEFAULT_BLUEPRINT, "encode-default-blueprint");

  yield* configRequestEffect(stateRef, {
    operation: "put",
    keys: ["flow-blueprint"],
    values: {
      default: defaultBlueprint,
    },
  });
});

const refreshBlueprintsFromConfigEffect = Effect.fn("FlowManager.refreshBlueprintsFromConfig")(function* (
  stateRef: SynchronizedRef.SynchronizedRef<FlowManagerServiceState>,
) {
  const response = yield* configRequestEffect(stateRef, {
    operation: "getvalues",
    type: "flow-blueprint",
  });
  const next = new Map<string, Blueprint>();

  for (const item of configValues(response)) {
    const blueprint = blueprintFromConfig(item.value);
    if (blueprint !== undefined) {
      next.set(item.key, blueprint);
    }
  }

  if (!next.has("default")) {
    next.set("default", DEFAULT_BLUEPRINT);
  }

  yield* SynchronizedRef.update(stateRef, (state) => ({
    ...state,
    blueprints: next,
  }));
});

const refreshFlowsFromConfigEffect = Effect.fn("FlowManager.refreshFlowsFromConfig")(function* (
  stateRef: SynchronizedRef.SynchronizedRef<FlowManagerServiceState>,
) {
  const response = yield* configRequestEffect(stateRef, {
    operation: "getvalues",
    type: "flow",
  });
  const next = new Map<string, FlowInstance>();

  for (const item of configValues(response)) {
    const flow = flowFromConfig(item.key, item.value);
    if (flow !== undefined) {
      next.set(item.key, flow);
    }
  }

  if (next.size === 0) {
    const flowsResponse = yield* configRequestEffect(stateRef, {
      operation: "getvalues",
      type: "flows",
    });
    for (const item of configValues(flowsResponse)) {
      next.set(item.key, {
        id: item.key,
        blueprintName: "default",
        description: "",
        parameters: {},
        status: "running",
      });
    }
  }

  yield* SynchronizedRef.update(stateRef, (state) => ({
    ...state,
    flows: next,
  }));
});

const handleListBlueprintsWithState = (state: FlowManagerServiceState): FlowResponse => ({
  "blueprint-names": [...state.blueprints.keys()],
});

const handleGetBlueprintEffect = Effect.fn("FlowManager.handleGetBlueprint")(function* (
  stateRef: SynchronizedRef.SynchronizedRef<FlowManagerServiceState>,
  request: FlowRequest,
) {
  const name = optionalString(request["blueprint-name"]);
  if (name === undefined) {
    return yield* flowManagerError("get-blueprint", "Missing blueprint-name");
  }

  const blueprint = (yield* SynchronizedRef.get(stateRef)).blueprints.get(name);
  if (blueprint === undefined) {
    return yield* flowManagerError("get-blueprint", `Blueprint not found: ${name}`);
  }

  const definition = yield* encodeJson(blueprint, "encode-blueprint");
  return {
    "blueprint-definition": definition,
  };
});

const handlePutBlueprintEffect = Effect.fn("FlowManager.handlePutBlueprint")(function* (
  stateRef: SynchronizedRef.SynchronizedRef<FlowManagerServiceState>,
  request: FlowRequest,
) {
  const name = optionalString(request["blueprint-name"]);
  if (name === undefined) {
    return yield* flowManagerError("put-blueprint", "Missing blueprint-name");
  }
  const rawDefinition = request["blueprint-definition"];
  if (rawDefinition === undefined) {
    return yield* flowManagerError("put-blueprint", "Missing blueprint-definition");
  }
  const definition = typeof rawDefinition === "string"
    ? rawDefinition
    : yield* encodeJson(rawDefinition, "encode-blueprint");

  yield* configRequestEffect(stateRef, {
    operation: "put",
    keys: ["flow-blueprint"],
    values: { [name]: definition },
  });
  yield* refreshBlueprintsFromConfigEffect(stateRef);
  return {};
});

const handleDeleteBlueprintEffect = Effect.fn("FlowManager.handleDeleteBlueprint")(function* (
  stateRef: SynchronizedRef.SynchronizedRef<FlowManagerServiceState>,
  request: FlowRequest,
) {
  const name = optionalString(request["blueprint-name"]);
  if (name === undefined) {
    return yield* flowManagerError("delete-blueprint", "Missing blueprint-name");
  }

  if (name === "default") {
    return yield* flowManagerError("delete-blueprint", "Cannot delete the default blueprint");
  }

  yield* configRequestEffect(stateRef, {
    operation: "delete",
    keys: ["flow-blueprint", name],
  });
  yield* SynchronizedRef.update(stateRef, (state) => {
    const blueprints = cloneBlueprints(state.blueprints);
    blueprints.delete(name);
    return {
      ...state,
      blueprints,
    };
  });

  return {};
});

const handleListFlowsWithState = (state: FlowManagerServiceState): FlowResponse => ({
  "flow-ids": [...state.flows.keys()],
});

const flowRecord = (inst: FlowInstance) => ({
  "blueprint-name": inst.blueprintName,
  description: inst.description,
  parameters: inst.parameters,
});

const handleGetFlowEffect = Effect.fn("FlowManager.handleGetFlow")(function* (
  stateRef: SynchronizedRef.SynchronizedRef<FlowManagerServiceState>,
  request: FlowRequest,
) {
  const id = optionalString(request["flow-id"]);
  if (id === undefined) {
    return yield* flowManagerError("get-flow", "Missing flow-id");
  }

  const inst = (yield* SynchronizedRef.get(stateRef)).flows.get(id);
  if (inst === undefined) {
    return yield* flowManagerError("get-flow", `Flow not found: ${id}`);
  }

  const flow = yield* encodeJson(flowRecord(inst), "encode-flow");
  return { flow };
});

const handleStartFlowEffect = Effect.fn("FlowManager.handleStartFlow")(function* (
  stateRef: SynchronizedRef.SynchronizedRef<FlowManagerServiceState>,
  request: FlowRequest,
) {
  const id = optionalString(request["flow-id"]);
  const blueprintName = optionalString(request["blueprint-name"]) ?? "default";
  const description = optionalString(request.description) ?? "";
  const parameters = isRecord(request.parameters) ? request.parameters : {};

  if (id === undefined) {
    return yield* flowManagerError("start-flow", "Missing flow-id");
  }

  const inst = yield* SynchronizedRef.modifyEffect(stateRef, (state) => {
    if (state.flows.has(id)) {
      return Effect.fail(flowManagerError("start-flow", `Flow already exists: ${id}`));
    }
    if (!state.blueprints.has(blueprintName)) {
      return Effect.fail(flowManagerError("start-flow", `Blueprint not found: ${blueprintName}`));
    }

    const next: FlowInstance = {
      id,
      blueprintName,
      description,
      parameters,
      status: "running",
    };
    const flows = cloneFlows(state.flows);
    flows.set(id, next);
    return Effect.succeed(modifyResult(next, {
      ...state,
      flows,
    }));
  });

  yield* Effect.log(`[FlowManager] Started flow "${inst.id}" with blueprint "${inst.blueprintName}"`);
  yield* pushFlowsConfigEffect(stateRef);

  return {};
});

const handleStopFlowEffect = Effect.fn("FlowManager.handleStopFlow")(function* (
  stateRef: SynchronizedRef.SynchronizedRef<FlowManagerServiceState>,
  request: FlowRequest,
) {
  const id = optionalString(request["flow-id"]);
  if (id === undefined) {
    return yield* flowManagerError("stop-flow", "Missing flow-id");
  }

  const inst = yield* SynchronizedRef.modifyEffect(stateRef, (state) => {
    const current = state.flows.get(id);
    if (current === undefined) {
      return Effect.fail(flowManagerError("stop-flow", `Flow not found: ${id}`));
    }

    const flows = cloneFlows(state.flows);
    flows.delete(id);
    return Effect.succeed(modifyResult(current, {
      ...state,
      flows,
    }));
  });

  yield* Effect.log(`[FlowManager] Stopped flow "${inst.id}"`);
  yield* deleteFlowConfigEffect(stateRef, id);
  yield* pushFlowsConfigEffect(stateRef);

  return {};
});

const pushFlowsConfigEffect = Effect.fn("FlowManager.pushFlowsConfig")(
  function* (
    stateRef: SynchronizedRef.SynchronizedRef<FlowManagerServiceState>,
  ) {
    const state = yield* SynchronizedRef.get(stateRef);
    const configClient = state.configClient;
    if (configClient === null) return;

    const flowsConfig: Record<string, { topics: Record<string, string> }> = {};
    const flowRecords: Record<string, string> = {};
    for (const [id, inst] of state.flows) {
      const blueprint = state.blueprints.get(inst.blueprintName);
      if (blueprint !== undefined) {
        flowsConfig[id] = { topics: blueprint.topics };
        flowRecords[id] = yield* encodeJson(flowRecord(inst), "encode-flow-config");
      }
    }

    yield* Effect.tryPromise({
      try: () =>
        configClient.request({
          operation: "put",
          keys: ["flows"],
          values: flowsConfig,
        }),
      catch: (cause) => flowManagerError("put-flows-config", cause),
    });
    yield* Effect.tryPromise({
      try: () =>
        configClient.request({
          operation: "put",
          keys: ["flow"],
          values: flowRecords,
        }),
      catch: (cause) => flowManagerError("put-flow-records", cause),
    });
    yield* Effect.log(`[FlowManager] Pushed flows config (${state.flows.size} active flows)`);
  },
  (effect) =>
    effect.pipe(
      Effect.catch((err) =>
        Effect.logError("[FlowManager] Failed to push flows config", { error: err.message }),
      ),
    ),
);

const deleteFlowConfigEffect = Effect.fn("FlowManager.deleteFlowConfig")(function* (
  stateRef: SynchronizedRef.SynchronizedRef<FlowManagerServiceState>,
  id: string,
) {
  const configClient = (yield* SynchronizedRef.get(stateRef)).configClient;
  if (configClient === null) return;
  yield* Effect.tryPromise({
    try: () =>
      configClient.request({
        operation: "delete",
        keys: ["flows", id],
      }),
    catch: (cause) => flowManagerError("delete-flows-config", cause),
  });
  yield* Effect.tryPromise({
    try: () =>
      configClient.request({
        operation: "delete",
        keys: ["flow", id],
      }),
    catch: (cause) => flowManagerError("delete-flow-record", cause),
  });
});

const closeFlowManagerResourcesEffect = Effect.fn("FlowManager.closeResources")(function* (
  stateRef: SynchronizedRef.SynchronizedRef<FlowManagerServiceState>,
) {
  const state = yield* SynchronizedRef.get(stateRef);

  const consumer = state.consumer;
  if (consumer !== null) {
    yield* Effect.tryPromise({
      try: () => consumer.close(),
      catch: (cause) => flowManagerError("consumer-close", cause),
    });
  }
  const responseProducer = state.responseProducer;
  if (responseProducer !== null) {
    yield* Effect.tryPromise({
      try: () => responseProducer.close(),
      catch: (cause) => flowManagerError("response-producer-close", cause),
    });
  }
  const configClient = state.configClient;
  if (configClient !== null) {
    yield* Effect.tryPromise({
      try: () => configClient.stop(),
      catch: (cause) => flowManagerError("config-client-stop", cause),
    });
  }

  yield* updateHandles(stateRef, {
    consumer: null,
    responseProducer: null,
    configClient: null,
  });
});

const consumeOnceEffect = Effect.fnUntraced(function* (
  service: FlowManagerService,
) {
  const consumer = (yield* SynchronizedRef.get(service.state)).consumer;
  if (consumer === null) {
    return yield* flowManagerError("consume", "Flow request consumer not started");
  }

  const msg = yield* Effect.tryPromise({
    try: () => consumer.receive(2000),
    catch: (cause) => flowManagerError("consume-receive", cause),
  });
  if (msg === null) return;

  yield* service.handleMessageEffect(msg);
  yield* Effect.tryPromise({
    try: () => consumer.acknowledge(msg),
    catch: (cause) => flowManagerError("consume-acknowledge", cause),
  });
});

const runFlowManagerServiceEffect = Effect.fn("FlowManager.runService")(function* (
  service: FlowManagerService,
) {
  const configClient = makeRequestResponse<ConfigRequest, ConfigResponse>({
    pubsub: service.pubsub,
    requestTopic: topics.configRequest,
    responseTopic: topics.configResponse,
    subscription: `${service.config.id}-config-client`,
  });
  yield* updateHandles(service.state, { configClient });
  yield* Effect.tryPromise({
    try: () => configClient.start(),
    catch: (cause) => flowManagerError("config-client-start", cause),
  });
  yield* ensureDefaultBlueprintEffect(service.state);
  yield* refreshBlueprintsFromConfigEffect(service.state);

  const responseProducer = yield* Effect.tryPromise({
    try: () =>
      service.pubsub.createProducer<FlowResponse>({
        topic: topics.flowResponse,
        schema: FlowResponseSchema,
      }),
    catch: (cause) => flowManagerError("response-producer", cause),
  });
  yield* updateHandles(service.state, { responseProducer });

  const consumer = yield* Effect.tryPromise({
    try: () =>
      service.pubsub.createConsumer<FlowRequest>({
        topic: topics.flowRequest,
        subscription: `${service.config.id}-flow-request`,
        schema: FlowRequestSchema,
      }),
    catch: (cause) => flowManagerError("consumer", cause),
  });
  yield* updateHandles(service.state, { consumer });

  yield* Effect.log(`[FlowManager] Listening on ${topics.flowRequest}`);

  yield* Effect.whileLoop({
    while: () => service.running,
    body: () =>
      consumeOnceEffect(service).pipe(
        Effect.catch((err) => {
          if (!service.running) return Effect.void;
          return Effect.logError("[FlowManager] Error in consume loop", { error: err.message }).pipe(
            Effect.flatMap(() => Effect.sleep(Duration.millis(1000))),
          );
        }),
      ),
    step: () => undefined,
  });
});

export function makeFlowManagerService(config: ProcessorConfig): FlowManagerService {
  const state = SynchronizedRef.makeUnsafe(initialState());
  let service: FlowManagerService | undefined;

  const getService = Effect.sync(() => service).pipe(
    Effect.flatMap((current) =>
      current === undefined
        ? Effect.fail(flowManagerError("service", "Flow manager service not initialized"))
        : Effect.succeed(current)
    ),
  );

  const base = makeAsyncProcessor<FlowManagerError>(config, {
    runEffect: () => getService.pipe(Effect.flatMap(runFlowManagerServiceEffect)),
  });
  const baseStop = base.stop;

  const handleOperationEffect = Effect.fn("FlowManager.handleOperation")(function* (request: FlowRequest) {
    const op = optionalString(request.operation);
    yield* refreshBlueprintsFromConfigEffect(state);
    yield* refreshFlowsFromConfigEffect(state);

    return yield* Match.value(op).pipe(
      Match.when("list-blueprints", () => Effect.succeed(handleListBlueprintsWithState(state.pipe(stateSnapshot)))),
      Match.when("put-blueprint", () => handlePutBlueprintEffect(state, request)),
      Match.when("get-blueprint", () => handleGetBlueprintEffect(state, request)),
      Match.when("delete-blueprint", () => handleDeleteBlueprintEffect(state, request)),
      Match.when("list-flows", () => Effect.succeed(handleListFlowsWithState(state.pipe(stateSnapshot)))),
      Match.when("get-flow", () => handleGetFlowEffect(state, request)),
      Match.when("start-flow", () => handleStartFlowEffect(state, request)),
      Match.when("stop-flow", () => handleStopFlowEffect(state, request)),
      Match.orElse(() => Effect.fail(flowManagerError("operation", `Unknown flow operation: ${op ?? ""}`))),
    );
  });

  const handleMessageEffect = Effect.fn("handleMessageEffect")(function* (msg: Message<FlowRequest>) {
    const request = yield* S.decodeUnknownEffect(FlowRequestSchema)(msg.value()).pipe(
      Effect.mapError((cause) => flowManagerError("decode", cause)),
    );
    const requestId = msg.properties().id;

    if (requestId === undefined || requestId.length === 0) {
      yield* Effect.logWarning("[FlowManager] Received request without id, ignoring");
      return;
    }

    const sendResponse = Effect.fnUntraced(function* (response: FlowResponse) {
      const responseProducer = (yield* SynchronizedRef.get(state)).responseProducer;
      if (responseProducer === null) {
        return yield* flowManagerError("respond", "Flow response producer not started");
      }
      yield* Effect.tryPromise({
        try: () => responseProducer.send(response, { id: requestId }),
        catch: (cause) => flowManagerError("respond", cause),
      });
    });

    yield* handleOperationEffect(request).pipe(
      Effect.flatMap(sendResponse),
      Effect.catch((err) =>
        sendResponse({
          error: { type: "flow-error", message: err.message },
        })
      ),
    );
  });

  const flowManagerService: FlowManagerService = Object.assign(base, {
    state,
    handleMessage: (msg: Message<FlowRequest>) => Effect.runPromise(handleMessageEffect(msg)),
    handleMessageEffect,
    configRequest: (request: ConfigRequest) => Effect.runPromise(configRequestEffect(state, request)),
    configRequestEffect: (request: ConfigRequest) => configRequestEffect(state, request),
    ensureDefaultBlueprint: () => Effect.runPromise(ensureDefaultBlueprintEffect(state)),
    ensureDefaultBlueprintEffect: ensureDefaultBlueprintEffect(state),
    refreshBlueprintsFromConfig: () => Effect.runPromise(refreshBlueprintsFromConfigEffect(state)),
    refreshBlueprintsFromConfigEffect: refreshBlueprintsFromConfigEffect(state),
    refreshFlowsFromConfig: () => Effect.runPromise(refreshFlowsFromConfigEffect(state)),
    refreshFlowsFromConfigEffect: refreshFlowsFromConfigEffect(state),
    handleOperation: (request: FlowRequest) => Effect.runPromise(handleOperationEffect(request)),
    handleOperationEffect,
    handleListBlueprints: () => handleListBlueprintsWithState(state.pipe(stateSnapshot)),
    handleGetBlueprint: (request: FlowRequest) => Effect.runPromise(handleGetBlueprintEffect(state, request)),
    handleGetBlueprintEffect: (request: FlowRequest) => handleGetBlueprintEffect(state, request),
    handlePutBlueprint: (request: FlowRequest) => Effect.runPromise(handlePutBlueprintEffect(state, request)),
    handlePutBlueprintEffect: (request: FlowRequest) => handlePutBlueprintEffect(state, request),
    handleDeleteBlueprint: (request: FlowRequest) => Effect.runPromise(handleDeleteBlueprintEffect(state, request)),
    handleDeleteBlueprintEffect: (request: FlowRequest) => handleDeleteBlueprintEffect(state, request),
    handleListFlows: () => handleListFlowsWithState(state.pipe(stateSnapshot)),
    handleGetFlow: (request: FlowRequest) => Effect.runPromise(handleGetFlowEffect(state, request)),
    handleGetFlowEffect: (request: FlowRequest) => handleGetFlowEffect(state, request),
    handleStartFlow: (request: FlowRequest) => Effect.runPromise(handleStartFlowEffect(state, request)),
    handleStartFlowEffect: (request: FlowRequest) => handleStartFlowEffect(state, request),
    handleStopFlow: (request: FlowRequest) => Effect.runPromise(handleStopFlowEffect(state, request)),
    handleStopFlowEffect: (request: FlowRequest) => handleStopFlowEffect(state, request),
    pushFlowsConfig: () => Effect.runPromise(pushFlowsConfigEffect(state)),
    pushFlowsConfigEffect: pushFlowsConfigEffect(state),
    deleteFlowConfig: (id: string) => Effect.runPromise(deleteFlowConfigEffect(state, id)),
    deleteFlowConfigEffect: (id: string) => deleteFlowConfigEffect(state, id),
    stop: () =>
      Effect.runPromise(
        closeFlowManagerResourcesEffect(state).pipe(
          Effect.flatMap(() =>
            Effect.tryPromise({
              try: () => baseStop(),
              catch: (cause) => flowManagerError("base-stop", cause),
            })
          ),
        ),
      ),
  });

  service = flowManagerService;
  return flowManagerService;
}

export const FlowManagerService = makeFlowManagerService;

export const program = makeProcessorProgram({
  id: "flow-manager",
  make: (config) => makeFlowManagerService(config),
});

const flowManagerRuntime = ManagedRuntime.make(Layer.empty);

export function run(): Promise<void> {
  return flowManagerRuntime.runPromise(program);
}

export function runMain(): void {
  NodeRuntime.runMain(program);
}
