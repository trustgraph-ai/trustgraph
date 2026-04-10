/**
 * Flow-aware processor that manages dynamic flow instances.
 *
 * Subscribes to config-push topic and dynamically creates/destroys
 * flow instances based on the configuration received.
 *
 * Python reference: trustgraph-base/trustgraph/base/flow_processor.py
 */

import { AsyncProcessor, type ProcessorConfig } from "./async-processor.js";
import type { Spec } from "../spec/types.js";
import type { BackendConsumer } from "../backend/types.js";
import { Flow, type FlowDefinition } from "./flow.js";
import { topics } from "../schema/topics.js";

interface ConfigPush {
  version: number;
  config: Record<string, unknown>;
}

export abstract class FlowProcessor extends AsyncProcessor {
  private specifications: Spec[] = [];
  private flows = new Map<string, Flow>();
  private configConsumer: BackendConsumer<ConfigPush> | null = null;
  private lastFlowsJson = "";

  protected constructor(config: ProcessorConfig) {
    super(config);
  }

  registerSpecification(spec: Spec): void {
    this.specifications.push(spec);
  }

  protected async run(): Promise<void> {
    // Subscribe to config-push topic to receive flow definitions.
    // Use "earliest" to replay any config pushes that arrived before this service started.
    this.configConsumer = await this.pubsub.createConsumer<ConfigPush>({
      topic: topics.configPush,
      subscription: `${this.config.id}-config-push`,
      initialPosition: "earliest",
    });

    console.log(`[${this.config.id}] Listening for config pushes on ${topics.configPush}`);

    while (this.running) {
      try {
        const msg = await this.configConsumer.receive(2000);
        if (!msg) continue;

        const push = msg.value();
        console.log(`[${this.config.id}] Received config push version=${push.version}`);

        await this.onConfigureFlows(push.config, push.version);

        // Also call any registered config handlers
        for (const handler of this.configHandlers) {
          await handler(push.config, push.version);
        }

        await this.configConsumer.acknowledge(msg);
      } catch (err) {
        if (!this.running) break;
        console.error(`[${this.config.id}] Config consumer error:`, err);
        await sleep(1000);
      }
    }
  }

  private async onConfigureFlows(
    config: Record<string, unknown>,
    version: number,
  ): Promise<void> {
    const flowDefs = config.flows as Record<string, FlowDefinition> | undefined;
    if (!flowDefs) {
      console.log(`[${this.config.id}] No flows in config push, skipping`);
      return;
    }

    // Skip flow restart if the flow definitions haven't changed.
    // This prevents disrupting in-flight requests when non-flow config
    // sections (prompts, tools, mcp) are updated.
    const flowsJson = JSON.stringify(flowDefs);
    if (this.lastFlowsJson && flowsJson === this.lastFlowsJson && this.flows.size > 0) {
      console.log(`[${this.config.id}] Flow definitions unchanged, skipping restart`);
      return;
    }
    this.lastFlowsJson = flowsJson;

    // Stop removed flows
    for (const [name, flow] of this.flows) {
      if (!(name in flowDefs)) {
        console.log(`[${this.config.id}] Stopping removed flow: ${name}`);
        await flow.stop();
        this.flows.delete(name);
      }
    }

    // Start or update flows
    for (const [name, defn] of Object.entries(flowDefs)) {
      // Skip invalid definitions (e.g., stringified JSON)
      if (typeof defn !== "object" || defn === null) {
        console.warn(`[${this.config.id}] Skipping flow "${name}": definition is not an object`);
        continue;
      }

      // Stop existing flow before (re)starting with new config
      if (this.flows.has(name)) {
        console.log(`[${this.config.id}] Restarting flow "${name}" with updated config`);
        await this.flows.get(name)!.stop();
        this.flows.delete(name);
      }

      console.log(`[${this.config.id}] Starting flow "${name}" with topics:`, defn.topics);
      const flow = new Flow(name, this.config.id, this.pubsub, defn, this.specifications);
      await flow.start();
      this.flows.set(name, flow);
      console.log(`[${this.config.id}] Flow "${name}" started`);
    }
  }

  override async stop(): Promise<void> {
    if (this.configConsumer) {
      await this.configConsumer.close();
      this.configConsumer = null;
    }
    for (const flow of this.flows.values()) {
      await flow.stop();
    }
    this.flows.clear();
    await super.stop();
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
