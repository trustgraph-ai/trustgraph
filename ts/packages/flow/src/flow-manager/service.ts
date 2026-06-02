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
  topics,
  makeRequestResponse,
  type ConfigRequest,
  type ConfigResponse,
  errorMessage,
} from "@trustgraph/base";
import { makeProcessorProgram } from "@trustgraph/base";
import type { Message } from "@trustgraph/base";
import { Context, Duration, Effect, Option } from "effect";
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

export type FlowManagerService = AsyncProcessorRuntime & Record<string, any>;

export function makeFlowManagerService(config: ProcessorConfig): FlowManagerService {
  const service = makeAsyncProcessor(config, {
    run: () => service.run(Context.empty()),
  }) as FlowManagerService;
  const baseStop = service.stop;
  service.flows = new Map<string, FlowInstance>();
  service.blueprints = new Map<string, Blueprint>();
  service.consumer = null;
  service.responseProducer = null;
  service.configClient = null;
  service.blueprints.set("default", DEFAULT_BLUEPRINT);
  Object.assign(service, {


      run: function(this: FlowManagerService): Promise<void> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            // Create config client for pushing flow configs to the config service
            service.configClient = makeRequestResponse<ConfigRequest, ConfigResponse>({
              pubsub: service.pubsub,
              requestTopic: topics.configRequest,
              responseTopic: topics.configResponse,
              subscription: `${service.config.id}-config-client`,
            });
            yield* Effect.tryPromise({
              try: () => service.configClient.start(),
              catch: (cause) => flowManagerError("config-client-start", cause),
            });
            yield* Effect.tryPromise({
              try: () => service.ensureDefaultBlueprint(),
              catch: (cause) => flowManagerError("ensure-default-blueprint", cause),
            });
            yield* Effect.tryPromise({
              try: () => service.refreshBlueprintsFromConfig(),
              catch: (cause) => flowManagerError("refresh-blueprints", cause),
            });

            // Create producer for flow-response topic
            service.responseProducer = yield* Effect.tryPromise({
              try: () =>
                service.pubsub.createProducer<Record<string, unknown>>({
                  topic: topics.flowResponse,
                }),
              catch: (cause) => flowManagerError("response-producer", cause),
            });

            // Create consumer for flow-request topic
            service.consumer = yield* Effect.tryPromise({
              try: () =>
                service.pubsub.createConsumer<Record<string, unknown>>({
                  topic: topics.flowRequest,
                  subscription: `${service.config.id}-flow-request`,
                }),
              catch: (cause) => flowManagerError("consumer", cause),
            });

            yield* Effect.log(`[FlowManager] Listening on ${topics.flowRequest}`);

            // Main consume loop (same pattern as ConfigService)
            while (service.running) {
              const shouldContinue = yield* Effect.gen(function* () {
                const consumer = service.consumer;
                if (consumer === null) {
                  return yield* flowManagerError("consume", "Flow request consumer not started");
                }

                const msg = yield* Effect.tryPromise({
                  try: () => consumer.receive(2000),
                  catch: (cause) => flowManagerError("consume-receive", cause),
                });
                if (msg === null) return true;

                yield* Effect.tryPromise({
                  try: () => service.handleMessage(msg),
                  catch: (cause) => flowManagerError("consume-handle", cause),
                });
                yield* Effect.tryPromise({
                  try: () => consumer.acknowledge(msg),
                  catch: (cause) => flowManagerError("consume-acknowledge", cause),
                });

                return true;
              }).pipe(
                Effect.catch((err) => {
                  if (!service.running) return Effect.succeed(false);
                  return Effect.logError("[FlowManager] Error in consume loop", { error: err.message }).pipe(
                    Effect.flatMap(() => Effect.sleep(Duration.millis(1000))),
                    Effect.as(true),
                  );
                }),
              );
              if (!shouldContinue) break;
            }
          }),
        );

        },



      handleMessage: function(this: FlowManagerService, msg: Message<Record<string, unknown>>): Promise<void> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const request = msg.value();
            const props = msg.properties();
            const requestId = props.id;

            if (requestId === undefined || requestId.length === 0) {
              yield* Effect.logWarning("[FlowManager] Received request without id, ignoring");
              return;
            }

            const sendResponse = (response: Record<string, unknown>): Effect.Effect<void, FlowManagerError> =>
              Effect.gen(function* () {
                const responseProducer = service.responseProducer;
                if (responseProducer === null) {
                  return yield* flowManagerError("respond", "Flow response producer not started");
                }
                yield* Effect.tryPromise({
                  try: () => responseProducer.send(response, { id: requestId }),
                  catch: (cause) => flowManagerError("respond", cause),
                });
              });

            yield* Effect.gen(function* () {
              const response = yield* Effect.tryPromise<Record<string, unknown>, FlowManagerError>({
                try: () => service.handleOperation(request),
                catch: (cause) => flowManagerError("operation", cause),
              });
              yield* sendResponse(response);
            }).pipe(
              Effect.catch((err) =>
                sendResponse({
                  error: { type: "flow-error", message: err.message },
                }),
              ),
            );
          }),
        );

        },



      configRequest: function(this: FlowManagerService, request: ConfigRequest): Promise<ConfigResponse> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const configClient = service.configClient;
            if (configClient === null) {
              return yield* flowManagerError("config-request", "Config client not started");
            }
            return yield* Effect.tryPromise<ConfigResponse, FlowManagerError>({
              try: () => configClient.request(request),
              catch: (cause) => flowManagerError("config-request", cause),
            });
          }),
        );

        },



      ensureDefaultBlueprint: function(this: FlowManagerService): Promise<void> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const response = yield* Effect.tryPromise<ConfigResponse, FlowManagerError>({
              try: () =>
                service.configRequest({
                  operation: "getvalues",
                  type: "flow-blueprint",
                }),
              catch: (cause) => flowManagerError("get-default-blueprint", cause),
            });
            if (configValues(response).some((value) => value.key === "default")) {
              return;
            }

            const defaultBlueprint = yield* encodeJson(DEFAULT_BLUEPRINT, "encode-default-blueprint");

            yield* Effect.tryPromise<ConfigResponse, FlowManagerError>({
              try: () =>
                service.configRequest({
                  operation: "put",
                  keys: ["flow-blueprint"],
                  values: {
                    default: defaultBlueprint,
                  },
                }),
              catch: (cause) => flowManagerError("put-default-blueprint", cause),
            });
          }),
        );

        },



      refreshBlueprintsFromConfig: function(this: FlowManagerService): Promise<void> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const response = yield* Effect.tryPromise<ConfigResponse, FlowManagerError>({
              try: () =>
                service.configRequest({
                  operation: "getvalues",
                  type: "flow-blueprint",
                }),
              catch: (cause) => flowManagerError("refresh-blueprints", cause),
            });
            const next = new Map<string, Blueprint>();

            for (const item of configValues(response)) {
              const parsed = parseConfigRecord(item.value);
              if (parsed === undefined) continue;
              next.set(item.key, parsed as Blueprint);
            }

            if (!next.has("default")) {
              next.set("default", DEFAULT_BLUEPRINT);
            }
            service.blueprints = next;
          }),
        );

        },



      refreshFlowsFromConfig: function(this: FlowManagerService): Promise<void> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const response = yield* Effect.tryPromise<ConfigResponse, FlowManagerError>({
              try: () =>
                service.configRequest({
                  operation: "getvalues",
                  type: "flow",
                }),
              catch: (cause) => flowManagerError("refresh-flows", cause),
            });
            const next = new Map<string, FlowInstance>();

            for (const item of configValues(response)) {
              const parsed = parseConfigRecord(item.value);
              if (parsed === undefined) continue;
              const parameters = isRecord(parsed.parameters) ? parsed.parameters : {};
              next.set(item.key, {
                id: item.key,
                blueprintName: optionalString(parsed["blueprint-name"]) ?? optionalString(parsed.blueprintName) ?? "default",
                description: optionalString(parsed.description) ?? "",
                parameters,
                status: "running",
              });
            }

            if (next.size === 0) {
              const flowsResponse = yield* Effect.tryPromise<ConfigResponse, FlowManagerError>({
                try: () =>
                  service.configRequest({
                    operation: "getvalues",
                    type: "flows",
                  }),
                catch: (cause) => flowManagerError("refresh-legacy-flows", cause),
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

            service.flows = next;
          }),
        );

        },



      handleOperation: function(this: FlowManagerService, request: Record<string, unknown>): Promise<Record<string, unknown>> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const op = optionalString(request.operation);
            yield* Effect.tryPromise({
              try: () => service.refreshBlueprintsFromConfig(),
              catch: (cause) => flowManagerError("refresh-blueprints", cause),
            });
            yield* Effect.tryPromise({
              try: () => service.refreshFlowsFromConfig(),
              catch: (cause) => flowManagerError("refresh-flows", cause),
            });

            switch (op) {
              case "list-blueprints":
                return service.handleListBlueprints();

              case "put-blueprint":
                return yield* Effect.tryPromise<Record<string, unknown>, FlowManagerError>({
                  try: () => service.handlePutBlueprint(request),
                  catch: (cause) => flowManagerError("put-blueprint", cause),
                });

              case "get-blueprint":
                return yield* Effect.tryPromise<Record<string, unknown>, FlowManagerError>({
                  try: () => service.handleGetBlueprint(request),
                  catch: (cause) => flowManagerError("get-blueprint", cause),
                });

              case "delete-blueprint":
                return yield* Effect.tryPromise<Record<string, unknown>, FlowManagerError>({
                  try: () => service.handleDeleteBlueprint(request),
                  catch: (cause) => flowManagerError("delete-blueprint", cause),
                });

              case "list-flows":
                return service.handleListFlows();

              case "get-flow":
                return yield* Effect.tryPromise<Record<string, unknown>, FlowManagerError>({
                  try: () => service.handleGetFlow(request),
                  catch: (cause) => flowManagerError("get-flow", cause),
                });

              case "start-flow":
                return yield* Effect.tryPromise<Record<string, unknown>, FlowManagerError>({
                  try: () => service.handleStartFlow(request),
                  catch: (cause) => flowManagerError("start-flow", cause),
                });

              case "stop-flow":
                return yield* Effect.tryPromise<Record<string, unknown>, FlowManagerError>({
                  try: () => service.handleStopFlow(request),
                  catch: (cause) => flowManagerError("stop-flow", cause),
                });

              default:
                return yield* flowManagerError("operation", `Unknown flow operation: ${op ?? ""}`);
            }
          }),
        );

        },



      // ---------- Blueprint operations ----------

      handleListBlueprints: function(this: FlowManagerService): Record<string, unknown> {
        return {
          "blueprint-names": [...this.blueprints.keys()],
        };

        },



      handleGetBlueprint: function(this: FlowManagerService, request: Record<string, unknown>): Promise<Record<string, unknown>> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const name = optionalString(request["blueprint-name"]);
            if (name === undefined) {
              return yield* flowManagerError("get-blueprint", "Missing blueprint-name");
            }

            const blueprint = service.blueprints.get(name);
            if (blueprint === undefined) {
              return yield* flowManagerError("get-blueprint", `Blueprint not found: ${name}`);
            }

            const definition = yield* encodeJson(blueprint, "encode-blueprint");
            return {
              "blueprint-definition": definition,
            };
          }),
        );

        },



      handlePutBlueprint: function(this: FlowManagerService, request: Record<string, unknown>): Promise<Record<string, unknown>> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
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

            yield* Effect.tryPromise({
              try: () =>
                service.configRequest({
                  operation: "put",
                  keys: ["flow-blueprint"],
                  values: { [name]: definition },
                }),
              catch: (cause) => flowManagerError("put-blueprint-config", cause),
            });
            yield* Effect.tryPromise({
              try: () => service.refreshBlueprintsFromConfig(),
              catch: (cause) => flowManagerError("refresh-blueprints", cause),
            });
            return {};
          }),
        );

        },



      handleDeleteBlueprint: function(this: FlowManagerService, request: Record<string, unknown>): Promise<Record<string, unknown>> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const name = optionalString(request["blueprint-name"]);
            if (name === undefined) {
              return yield* flowManagerError("delete-blueprint", "Missing blueprint-name");
            }

            if (name === "default") {
              return yield* flowManagerError("delete-blueprint", "Cannot delete the default blueprint");
            }

            yield* Effect.tryPromise({
              try: () =>
                service.configRequest({
                  operation: "delete",
                  keys: ["flow-blueprint", name],
                }),
              catch: (cause) => flowManagerError("delete-blueprint-config", cause),
            });
            service.blueprints.delete(name);

            return {};
          }),
        );

        },



      // ---------- Flow operations ----------

      handleListFlows: function(this: FlowManagerService): Record<string, unknown> {
        return {
          "flow-ids": [...this.flows.keys()],
        };

        },



      handleGetFlow: function(this: FlowManagerService, request: Record<string, unknown>): Promise<Record<string, unknown>> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const id = optionalString(request["flow-id"]);
            if (id === undefined) {
              return yield* flowManagerError("get-flow", "Missing flow-id");
            }

            const inst = service.flows.get(id);
            if (inst === undefined) {
              return yield* flowManagerError("get-flow", `Flow not found: ${id}`);
            }

            const flow = yield* encodeJson(
              {
                "blueprint-name": inst.blueprintName,
                description: inst.description,
                parameters: inst.parameters,
              },
              "encode-flow",
            );

            return { flow };
          }),
        );

        },



      handleStartFlow: function(this: FlowManagerService, request: Record<string, unknown>): Promise<Record<string, unknown>> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const id = optionalString(request["flow-id"]);
            const blueprintName = optionalString(request["blueprint-name"]) ?? "default";
            const description = optionalString(request.description) ?? "";
            const parameters = isRecord(request.parameters) ? request.parameters : {};

            if (id === undefined) {
              return yield* flowManagerError("start-flow", "Missing flow-id");
            }

            if ((service.flows as Map<string, FlowInstance>).has(id)) {
              return yield* flowManagerError("start-flow", `Flow already exists: ${id}`);
            }

            const blueprint = service.blueprints.get(blueprintName);
            if (blueprint === undefined) {
              return yield* flowManagerError("start-flow", `Blueprint not found: ${blueprintName}`);
            }

            // Create the flow instance
            const inst: FlowInstance = {
              id,
              blueprintName,
              description,
              parameters,
              status: "running",
            };
            service.flows.set(id, inst);

            yield* Effect.log(
              `[FlowManager] Started flow "${id}" with blueprint "${blueprintName}"`,
            );

            // Push updated flows config to the config service
            yield* Effect.tryPromise({
              try: () => service.pushFlowsConfig(),
              catch: (cause) => flowManagerError("push-flows-config", cause),
            });

            return {};
          }),
        );

        },



      handleStopFlow: function(this: FlowManagerService, request: Record<string, unknown>): Promise<Record<string, unknown>> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const id = optionalString(request["flow-id"]);
            if (id === undefined) {
              return yield* flowManagerError("stop-flow", "Missing flow-id");
            }

            const inst = service.flows.get(id);
            if (inst === undefined) {
              return yield* flowManagerError("stop-flow", `Flow not found: ${id}`);
            }

            service.flows.delete(id);

            yield* Effect.log(`[FlowManager] Stopped flow "${id}"`);

            yield* Effect.tryPromise({
              try: () => service.deleteFlowConfig(id),
              catch: (cause) => flowManagerError("delete-flow-config", cause),
            });

            // Push updated flows config (without the removed flow)
            yield* Effect.tryPromise({
              try: () => service.pushFlowsConfig(),
              catch: (cause) => flowManagerError("push-flows-config", cause),
            });

            return {};
          }),
        );

        },



      // ---------- Config push ----------

      /**
       * Build the flows config object from all running flows and push it
       * to the config service via a PUT operation.
       */
      pushFlowsConfig: function(this: FlowManagerService): Promise<void> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const configClient = service.configClient;
            if (configClient === null) return;

            const flowsConfig: Record<string, { topics: Record<string, string> }> = {};
            const flowRecords: Record<string, string> = {};
            for (const [id, inst] of service.flows) {
              const blueprint = service.blueprints.get(inst.blueprintName);
              if (blueprint !== undefined) {
                flowsConfig[id] = { topics: blueprint.topics };
                flowRecords[id] = yield* encodeJson(
                  {
                    "blueprint-name": inst.blueprintName,
                    description: inst.description,
                    parameters: inst.parameters,
                  },
                  "encode-flow-config",
                );
              }
            }

            yield* Effect.gen(function* () {
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
              yield* Effect.log(
                `[FlowManager] Pushed flows config (${service.flows.size} active flows)`,
              );
            }).pipe(
              Effect.catch((err) =>
                Effect.logError("[FlowManager] Failed to push flows config", { error: err.message }),
              ),
            );
          }),
        );

        },



      deleteFlowConfig: function(this: FlowManagerService, id: string): Promise<void> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            const configClient = service.configClient;
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
          }),
        );

        },



      // ---------- Lifecycle ----------

      stop: function(this: FlowManagerService): Promise<void> {
        const service = this;
        return Effect.runPromise(
          Effect.gen(function* () {
            if (service.consumer !== null) {
              const consumer = service.consumer;
              yield* Effect.tryPromise({
                try: () => consumer.close(),
                catch: (cause) => flowManagerError("consumer-close", cause),
              });
              service.consumer = null;
            }
            if (service.responseProducer !== null) {
              const responseProducer = service.responseProducer;
              yield* Effect.tryPromise({
                try: () => responseProducer.close(),
                catch: (cause) => flowManagerError("response-producer-close", cause),
              });
              service.responseProducer = null;
            }
            if (service.configClient !== null) {
              const configClient = service.configClient;
              yield* Effect.tryPromise({
                try: () => configClient.stop(),
                catch: (cause) => flowManagerError("config-client-stop", cause),
              });
              service.configClient = null;
            }
            yield* Effect.tryPromise({
              try: () => baseStop(),
              catch: (cause) => flowManagerError("base-stop", cause),
            });
          }),
        );

        }
  });
  return service;
}

export const FlowManagerService = makeFlowManagerService;

export const program = makeProcessorProgram({
  id: "flow-manager",
  make: (config) => makeFlowManagerService(config),
});

export function run(): Promise<void> {
  return Effect.runPromise(program);
}
