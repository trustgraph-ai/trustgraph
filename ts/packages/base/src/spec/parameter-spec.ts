/**
 * Parameter specification — declares a configuration parameter for a flow.
 *
 * Python reference: trustgraph-base/trustgraph/base/parameter_spec.py
 */

import type { Spec } from "./types.js";
import type { PubSubBackend } from "../backend/types.js";
import type { Flow, FlowDefinition } from "../processor/flow.js";

export class ParameterSpec implements Spec {
  constructor(public readonly name: string) {}

  async add(flow: Flow, _pubsub: PubSubBackend, definition: FlowDefinition): Promise<void> {
    const value = definition.parameters?.[this.name];
    flow.setParameter(this.name, value);
  }
}
