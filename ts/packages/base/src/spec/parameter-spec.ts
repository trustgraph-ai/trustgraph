/**
 * Parameter specification — declares a configuration parameter for a flow.
 *
 * Python reference: trustgraph-base/trustgraph/base/parameter_spec.py
 */

import { Effect } from "effect";
import type { Spec } from "./types.js";
import type { Flow, FlowDefinition } from "../processor/flow.js";

export interface ParameterSpec extends Spec {}

export function makeParameterSpec(name: string): ParameterSpec {
  const addEffect = (flow: Flow, definition: FlowDefinition) =>
    Effect.sync(() => {
      const value = definition.parameters?.[name];
      flow.setParameter(name, value);
    });

  return {
    name,
    addEffect,
    add: (flow, _pubsub, definition) => Effect.runPromise(addEffect(flow, definition)),
  };
}
