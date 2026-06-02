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
} from "@trustgraph/base";
import { makeProcessorProgram } from "@trustgraph/base";
import type { Message } from "@trustgraph/base";
import { Effect } from "effect";

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
  try {
    const parsed = typeof value === "string" ? JSON.parse(value) as unknown : value;
    return isRecord(parsed) ? parsed : undefined;
  } catch {
    return undefined;
  }
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
    run: async () => {
      await service.run();
    },
  }) as FlowManagerService;
  const baseStop = service.stop;
  service.flows = new Map<string, FlowInstance>();
  service.blueprints = new Map<string, Blueprint>();
  service.consumer = null;
  service.responseProducer = null;
  service.configClient = null;
  service.blueprints.set("default", DEFAULT_BLUEPRINT);
  Object.assign(service, {


      run: async function(this: FlowManagerService): Promise<void> {
        // Create config client for pushing flow configs to the config service
        this.configClient = makeRequestResponse<ConfigRequest, ConfigResponse>({
          pubsub: this.pubsub,
          requestTopic: topics.configRequest,
          responseTopic: topics.configResponse,
          subscription: `${this.config.id}-config-client`,
        });
        await this.configClient.start();
        await this.ensureDefaultBlueprint();
        await this.refreshBlueprintsFromConfig();

        // Create producer for flow-response topic
        this.responseProducer = await this.pubsub.createProducer<Record<string, unknown>>({
          topic: topics.flowResponse,
        });

        // Create consumer for flow-request topic
        this.consumer = await this.pubsub.createConsumer<Record<string, unknown>>({
          topic: topics.flowRequest,
          subscription: `${this.config.id}-flow-request`,
        });

        console.log(`[FlowManager] Listening on ${topics.flowRequest}`);

        // Main consume loop (same pattern as ConfigService)
        while (this.running) {
          try {
            const msg = await this.consumer.receive(2000);
            if (msg === null) continue;

            await this.handleMessage(msg);
            await this.consumer.acknowledge(msg);
          } catch (err) {
            if (!this.running) break;
            console.error("[FlowManager] Error in consume loop:", err);
            await sleep(1000);
          }
        }

        },



      handleMessage: async function(this: FlowManagerService, msg: Message<Record<string, unknown>>): Promise<void> {
        const request = msg.value();
        const props = msg.properties();
        const requestId = props.id;

        if (requestId === undefined || requestId.length === 0) {
          console.warn("[FlowManager] Received request without id, ignoring");
          return;
        }

        try {
          const response = await this.handleOperation(request);
          await this.responseProducer!.send(response, { id: requestId });
        } catch (err) {
          const message = err instanceof Error ? err.message : String(err);
          await this.responseProducer!.send(
            {
              error: { type: "flow-error", message },
            },
            { id: requestId },
          );
        }

        },



      configRequest: async function(this: FlowManagerService, request: ConfigRequest): Promise<ConfigResponse> {
        if (this.configClient === null) throw new Error("Config client not started");
        return this.configClient.request(request);

        },



      ensureDefaultBlueprint: async function(this: FlowManagerService): Promise<void> {
        const response = await this.configRequest({
          operation: "getvalues",
          type: "flow-blueprint",
        });
        if (configValues(response).some((value) => value.key === "default")) {
          return;
        }

        await this.configRequest({
          operation: "put",
          keys: ["flow-blueprint"],
          values: {
            default: JSON.stringify(DEFAULT_BLUEPRINT),
          },
        });

        },



      refreshBlueprintsFromConfig: async function(this: FlowManagerService): Promise<void> {
        const response = await this.configRequest({
          operation: "getvalues",
          type: "flow-blueprint",
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
        this.blueprints = next;

        },



      refreshFlowsFromConfig: async function(this: FlowManagerService): Promise<void> {
        const response = await this.configRequest({
          operation: "getvalues",
          type: "flow",
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
          const flowsResponse = await this.configRequest({
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

        this.flows = next;

        },



      handleOperation: async function(this: FlowManagerService, request: Record<string, unknown>): Promise<Record<string, unknown>> {
        const op = request.operation as string;
        await this.refreshBlueprintsFromConfig();
        await this.refreshFlowsFromConfig();

        switch (op) {
          case "list-blueprints":
            return this.handleListBlueprints();

          case "put-blueprint":
            return await this.handlePutBlueprint(request);

          case "get-blueprint":
            return this.handleGetBlueprint(request);

          case "delete-blueprint":
            return this.handleDeleteBlueprint(request);

          case "list-flows":
            return this.handleListFlows();

          case "get-flow":
            return this.handleGetFlow(request);

          case "start-flow":
            return await this.handleStartFlow(request);

          case "stop-flow":
            return await this.handleStopFlow(request);

          default:
            throw new Error(`Unknown flow operation: ${op}`);
        }

        },



      // ---------- Blueprint operations ----------

      handleListBlueprints: function(this: FlowManagerService): Record<string, unknown> {
        return {
          "blueprint-names": [...this.blueprints.keys()],
        };

        },



      handleGetBlueprint: function(this: FlowManagerService, request: Record<string, unknown>): Record<string, unknown> {
        const name = request["blueprint-name"] as string | undefined;
        if (name === undefined || name.length === 0) {
          throw new Error("Missing blueprint-name");
        }

        const blueprint = this.blueprints.get(name);
        if (blueprint === undefined) {
          throw new Error(`Blueprint not found: ${name}`);
        }

        return {
          "blueprint-definition": JSON.stringify(blueprint),
        };

        },



      handlePutBlueprint: async function(this: FlowManagerService, request: Record<string, unknown>): Promise<Record<string, unknown>> {
        const name = request["blueprint-name"] as string | undefined;
        if (name === undefined || name.length === 0) {
          throw new Error("Missing blueprint-name");
        }
        const rawDefinition = request["blueprint-definition"];
        if (rawDefinition === undefined) {
          throw new Error("Missing blueprint-definition");
        }
        const definition = typeof rawDefinition === "string"
          ? rawDefinition
          : JSON.stringify(rawDefinition);

        await this.configRequest({
          operation: "put",
          keys: ["flow-blueprint"],
          values: { [name]: definition },
        });
        await this.refreshBlueprintsFromConfig();
        return {};

        },



      handleDeleteBlueprint: async function(this: FlowManagerService, request: Record<string, unknown>): Promise<Record<string, unknown>> {
        const name = request["blueprint-name"] as string | undefined;
        if (name === undefined || name.length === 0) {
          throw new Error("Missing blueprint-name");
        }

        if (name === "default") {
          throw new Error("Cannot delete the default blueprint");
        }

        await this.configRequest({
          operation: "delete",
          keys: ["flow-blueprint", name],
        });
        this.blueprints.delete(name);

        return {};

        },



      // ---------- Flow operations ----------

      handleListFlows: function(this: FlowManagerService): Record<string, unknown> {
        return {
          "flow-ids": [...this.flows.keys()],
        };

        },



      handleGetFlow: function(this: FlowManagerService, request: Record<string, unknown>): Record<string, unknown> {
        const id = request["flow-id"] as string | undefined;
        if (id === undefined || id.length === 0) {
          throw new Error("Missing flow-id");
        }

        const inst = this.flows.get(id);
        if (inst === undefined) {
          throw new Error(`Flow not found: ${id}`);
        }

        return {
          flow: JSON.stringify({
            "blueprint-name": inst.blueprintName,
            description: inst.description,
            parameters: inst.parameters,
          }),
        };

        },



      handleStartFlow: async function(this: FlowManagerService, request: Record<string, unknown>): Promise<Record<string, unknown>> {
        const id = request["flow-id"] as string | undefined;
        const blueprintName = (request["blueprint-name"] as string) ?? "default";
        const description = (request["description"] as string) ?? "";
        const parameters = (request["parameters"] as Record<string, unknown>) ?? {};

        if (id === undefined || id.length === 0) {
          throw new Error("Missing flow-id");
        }

        if ((this.flows as Map<string, FlowInstance>).has(id)) {
          throw new Error(`Flow already exists: ${id}`);
        }

        const blueprint = this.blueprints.get(blueprintName);
        if (blueprint === undefined) {
          throw new Error(`Blueprint not found: ${blueprintName}`);
        }

        // Create the flow instance
        const inst: FlowInstance = {
          id,
          blueprintName,
          description,
          parameters,
          status: "running",
        };
        this.flows.set(id, inst);

        console.log(
          `[FlowManager] Started flow "${id}" with blueprint "${blueprintName}"`,
        );

        // Push updated flows config to the config service
        await this.pushFlowsConfig();

        return {};

        },



      handleStopFlow: async function(this: FlowManagerService, request: Record<string, unknown>): Promise<Record<string, unknown>> {
        const id = request["flow-id"] as string | undefined;
        if (id === undefined || id.length === 0) {
          throw new Error("Missing flow-id");
        }

        const inst = this.flows.get(id);
        if (inst === undefined) {
          throw new Error(`Flow not found: ${id}`);
        }

        this.flows.delete(id);

        console.log(`[FlowManager] Stopped flow "${id}"`);

        await this.deleteFlowConfig(id);

        // Push updated flows config (without the removed flow)
        await this.pushFlowsConfig();

        return {};

        },



      // ---------- Config push ----------

      /**
       * Build the flows config object from all running flows and push it
       * to the config service via a PUT operation.
       */
      pushFlowsConfig: async function(this: FlowManagerService): Promise<void> {
        if (this.configClient === null) return;

        const flowsConfig: Record<string, { topics: Record<string, string> }> = {};
        const flowRecords: Record<string, string> = {};
        for (const [id, inst] of this.flows) {
          const blueprint = this.blueprints.get(inst.blueprintName);
          if (blueprint !== undefined) {
            flowsConfig[id] = { topics: blueprint.topics };
            flowRecords[id] = JSON.stringify({
              "blueprint-name": inst.blueprintName,
              description: inst.description,
              parameters: inst.parameters,
            });
          }
        }

        try {
          await this.configClient.request({
            operation: "put",
            keys: ["flows"],
            values: flowsConfig,
          });
          await this.configClient.request({
            operation: "put",
            keys: ["flow"],
            values: flowRecords,
          });
          console.log(
            `[FlowManager] Pushed flows config (${this.flows.size} active flows)`,
          );
        } catch (err) {
          console.error("[FlowManager] Failed to push flows config:", err);
        }

        },



      deleteFlowConfig: async function(this: FlowManagerService, id: string): Promise<void> {
        if (this.configClient === null) return;
        await this.configClient.request({
          operation: "delete",
          keys: ["flows", id],
        });
        await this.configClient.request({
          operation: "delete",
          keys: ["flow", id],
        });

        },



      // ---------- Lifecycle ----------

      stop: async function(this: FlowManagerService): Promise<void> {
        if (this.consumer !== null) {
          await this.consumer.close();
          this.consumer = null;
        }
        if (this.responseProducer !== null) {
          await this.responseProducer.close();
          this.responseProducer = null;
        }
        if (this.configClient !== null) {
          await this.configClient.stop();
          this.configClient = null;
        }
        await baseStop();

        }
  });
  return service;
}

export const FlowManagerService = makeFlowManagerService;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export const program = makeProcessorProgram({
  id: "flow-manager",
  make: (config) => makeFlowManagerService(config),
});

export async function run(): Promise<void> {
  await Effect.runPromise(program);
}
