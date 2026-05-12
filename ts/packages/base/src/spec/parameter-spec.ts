/**
 * Parameter specification — declares a configuration parameter for a flow.
 *
 * Python reference: trustgraph-base/trustgraph/base/parameter_spec.py
 */

import { Effect } from "effect";
import type { Spec } from "./types.js";
import type { PubSubBackend } from "../backend/types.js";
import type { Flow, FlowDefinition } from "../processor/flow.js";

export class ParameterSpec implements Spec {
  public readonly name: string;

  constructor(name: string) {
    this.name = name;
  }

  addEffect(flow: Flow, definition: FlowDefinition) {
    const spec = this;
    return Effect.sync(() => {
      const value = definition.parameters?.[spec.name];
      flow.setParameter(spec.name, value);
    });
  }

  async add(flow: Flow, _pubsub: PubSubBackend, definition: FlowDefinition): Promise<void> {
    await Effect.runPromise(this.addEffect(flow, definition));
  }
}
