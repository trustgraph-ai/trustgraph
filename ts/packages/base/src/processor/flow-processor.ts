/**
 * Flow-aware processor that manages dynamic flow instances.
 *
 * Python reference: trustgraph-base/trustgraph/base/flow_processor.py
 */

import { AsyncProcessor, type ProcessorConfig } from "./async-processor.js";
import type { Spec } from "../spec/types.js";
import { Flow, type FlowDefinition } from "./flow.js";

export abstract class FlowProcessor extends AsyncProcessor {
  private specifications: Spec[] = [];
  private flows = new Map<string, Flow>();

  constructor(config: ProcessorConfig) {
    super(config);
    this.registerConfigHandler(this.onConfigureFlows.bind(this));
  }

  registerSpecification(spec: Spec): void {
    this.specifications.push(spec);
  }

  protected async run(): Promise<void> {
    // The processor sits idle waiting for flow configurations
    // to arrive via the config push topic. In the meantime,
    // the consumer loop runs in the background.
    await new Promise<void>((resolve) => {
      const check = () => {
        if (!this.running) resolve();
        else setTimeout(check, 1000);
      };
      check();
    });
  }

  private async onConfigureFlows(
    config: Record<string, unknown>,
    version: number,
  ): Promise<void> {
    const flowDefs = config.flows as Record<string, FlowDefinition> | undefined;
    if (!flowDefs) return;

    // Stop removed flows
    for (const [name, flow] of this.flows) {
      if (!(name in flowDefs)) {
        await flow.stop();
        this.flows.delete(name);
      }
    }

    // Start new flows
    for (const [name, defn] of Object.entries(flowDefs)) {
      if (!this.flows.has(name)) {
        const flow = new Flow(name, this.config.id, this.pubsub, defn, this.specifications);
        await flow.start();
        this.flows.set(name, flow);
      }
    }
  }

  override async stop(): Promise<void> {
    for (const flow of this.flows.values()) {
      await flow.stop();
    }
    this.flows.clear();
    await super.stop();
  }
}
