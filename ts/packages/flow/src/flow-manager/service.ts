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
  AsyncProcessor,
  type ProcessorConfig,
  topics,
  RequestResponse,
  type ConfigRequest,
  type ConfigResponse,
} from "@trustgraph/base";
import type {
  BackendProducer,
  BackendConsumer,
  Message,
} from "@trustgraph/base";

// ---------- Internal state types ----------

interface FlowInstance {
  id: string;
  blueprintName: string;
  description: string;
  parameters: Record<string, string>;
  status: "running" | "stopped";
}

interface Blueprint {
  description: string;
  topics: Record<string, string>;
}

// ---------- Default blueprint ----------

const DEFAULT_BLUEPRINT: Blueprint = {
  description: "Default processing pipeline with all services",
  topics: {
    "request": "tg.flow.text-completion-request",
    "response": "tg.flow.text-completion-response",
    "prompt-request": "tg.flow.prompt-request",
    "prompt-response": "tg.flow.prompt-response",
    "graph-rag-request": "tg.flow.graph-rag-request",
    "graph-rag-response": "tg.flow.graph-rag-response",
    "document-rag-request": "tg.flow.document-rag-request",
    "document-rag-response": "tg.flow.document-rag-response",
    "triples-request": "tg.flow.triples-request",
    "triples-response": "tg.flow.triples-response",
    "text-completion-request": "tg.flow.text-completion-request",
    "text-completion-response": "tg.flow.text-completion-response",
    "input": "tg.flow.chunk",
    "output": "tg.flow.chunk",
    "triples": "tg.flow.triples",
    "entity-contexts": "tg.flow.entity-contexts",
  },
};

// ---------- Service ----------

export class FlowManagerService extends AsyncProcessor {
  private flows = new Map<string, FlowInstance>();
  private blueprints = new Map<string, Blueprint>();

  private consumer: BackendConsumer<Record<string, unknown>> | null = null;
  private responseProducer: BackendProducer<Record<string, unknown>> | null = null;
  private configClient: RequestResponse<ConfigRequest, ConfigResponse> | null = null;

  constructor(config: ProcessorConfig) {
    super(config);
    this.blueprints.set("default", DEFAULT_BLUEPRINT);
  }

  protected override async run(): Promise<void> {
    // Create config client for pushing flow configs to the config service
    this.configClient = new RequestResponse<ConfigRequest, ConfigResponse>({
      pubsub: this.pubsub,
      requestTopic: topics.configRequest,
      responseTopic: topics.configResponse,
      subscription: `${this.config.id}-config-client`,
    });
    await this.configClient.start();

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
        if (!msg) continue;

        await this.handleMessage(msg);
        await this.consumer.acknowledge(msg);
      } catch (err) {
        if (!this.running) break;
        console.error("[FlowManager] Error in consume loop:", err);
        await sleep(1000);
      }
    }
  }

  private async handleMessage(
    msg: Message<Record<string, unknown>>,
  ): Promise<void> {
    const request = msg.value();
    const props = msg.properties();
    const requestId = props.id;

    if (!requestId) {
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
  }

  private async handleOperation(
    request: Record<string, unknown>,
  ): Promise<Record<string, unknown>> {
    const op = request.operation as string;

    switch (op) {
      case "list-blueprints":
        return this.handleListBlueprints();

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
  }

  // ---------- Blueprint operations ----------

  private handleListBlueprints(): Record<string, unknown> {
    return {
      "blueprint-names": [...this.blueprints.keys()],
    };
  }

  private handleGetBlueprint(
    request: Record<string, unknown>,
  ): Record<string, unknown> {
    const name = request["blueprint-name"] as string | undefined;
    if (!name) {
      throw new Error("Missing blueprint-name");
    }

    const blueprint = this.blueprints.get(name);
    if (!blueprint) {
      throw new Error(`Blueprint not found: ${name}`);
    }

    return {
      "blueprint-definition": JSON.stringify(blueprint),
    };
  }

  private handleDeleteBlueprint(
    request: Record<string, unknown>,
  ): Record<string, unknown> {
    const name = request["blueprint-name"] as string | undefined;
    if (!name) {
      throw new Error("Missing blueprint-name");
    }

    if (name === "default") {
      throw new Error("Cannot delete the default blueprint");
    }

    const existed = this.blueprints.delete(name);
    if (!existed) {
      throw new Error(`Blueprint not found: ${name}`);
    }

    return {};
  }

  // ---------- Flow operations ----------

  private handleListFlows(): Record<string, unknown> {
    return {
      "flow-ids": [...this.flows.keys()],
    };
  }

  private handleGetFlow(
    request: Record<string, unknown>,
  ): Record<string, unknown> {
    const id = request["flow-id"] as string | undefined;
    if (!id) {
      throw new Error("Missing flow-id");
    }

    const inst = this.flows.get(id);
    if (!inst) {
      throw new Error(`Flow not found: ${id}`);
    }

    return {
      flow: JSON.stringify({
        "blueprint-name": inst.blueprintName,
        description: inst.description,
        parameters: inst.parameters,
      }),
    };
  }

  private async handleStartFlow(
    request: Record<string, unknown>,
  ): Promise<Record<string, unknown>> {
    const id = request["flow-id"] as string | undefined;
    const blueprintName = (request["blueprint-name"] as string) ?? "default";
    const description = (request["description"] as string) ?? "";
    const parameters = (request["parameters"] as Record<string, string>) ?? {};

    if (!id) {
      throw new Error("Missing flow-id");
    }

    if (this.flows.has(id)) {
      throw new Error(`Flow already exists: ${id}`);
    }

    const blueprint = this.blueprints.get(blueprintName);
    if (!blueprint) {
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
  }

  private async handleStopFlow(
    request: Record<string, unknown>,
  ): Promise<Record<string, unknown>> {
    const id = request["flow-id"] as string | undefined;
    if (!id) {
      throw new Error("Missing flow-id");
    }

    const inst = this.flows.get(id);
    if (!inst) {
      throw new Error(`Flow not found: ${id}`);
    }

    this.flows.delete(id);

    console.log(`[FlowManager] Stopped flow "${id}"`);

    // Push updated flows config (without the removed flow)
    await this.pushFlowsConfig();

    return {};
  }

  // ---------- Config push ----------

  /**
   * Build the flows config object from all running flows and push it
   * to the config service via a PUT operation.
   */
  private async pushFlowsConfig(): Promise<void> {
    if (!this.configClient) return;

    const flowsConfig: Record<string, { topics: Record<string, string> }> = {};
    for (const [id, inst] of this.flows) {
      const blueprint = this.blueprints.get(inst.blueprintName);
      if (blueprint) {
        flowsConfig[id] = { topics: blueprint.topics };
      }
    }

    try {
      await this.configClient.request({
        operation: "put",
        keys: ["flows"],
        values: flowsConfig,
      });
      console.log(
        `[FlowManager] Pushed flows config (${this.flows.size} active flows)`,
      );
    } catch (err) {
      console.error("[FlowManager] Failed to push flows config:", err);
    }
  }

  // ---------- Lifecycle ----------

  override async stop(): Promise<void> {
    if (this.consumer) {
      await this.consumer.close();
      this.consumer = null;
    }
    if (this.responseProducer) {
      await this.responseProducer.close();
      this.responseProducer = null;
    }
    if (this.configClient) {
      await this.configClient.stop();
      this.configClient = null;
    }
    await super.stop();
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function run(): Promise<void> {
  await FlowManagerService.launch("flow-manager");
}
