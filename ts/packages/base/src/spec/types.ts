/**
 * Specification types for declarative flow configuration.
 *
 * Python reference: trustgraph-base/trustgraph/base/spec.py and siblings
 */

import type { PubSubBackend } from "../backend/types.js";
import type { Flow, FlowDefinition } from "../processor/flow.js";

export interface Spec {
  name: string;
  add(flow: Flow, pubsub: PubSubBackend, definition: FlowDefinition): Promise<void>;
}
