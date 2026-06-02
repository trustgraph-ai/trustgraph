/**
 * Specification types for declarative flow configuration.
 *
 * Python reference: trustgraph-base/trustgraph/base/spec.py and siblings
 */

import type { Context, Effect, Scope } from "effect";
import type { PubSubBackend } from "../backend/types.js";
import type {
  ConsumerFactory,
  ProducerFactory,
  RequestResponseFactory,
} from "../messaging/runtime.js";
import type { Flow, FlowDefinition } from "../processor/flow.js";
import type { PubSubError } from "../errors.js";

export type SpecRuntimeRequirements =
  | Scope.Scope
  | ProducerFactory
  | ConsumerFactory
  | RequestResponseFactory;

export type SpecRuntimeError = PubSubError;

export interface Spec<Requirements = never> {
  name: string;
  addEffect(
    flow: Flow<Requirements>,
    definition: FlowDefinition,
  ): Effect.Effect<void, SpecRuntimeError, SpecRuntimeRequirements | Requirements>;
  add(
    flow: Flow<Requirements>,
    pubsub: PubSubBackend,
    definition: FlowDefinition,
    context: Context.Context<Requirements>,
  ): Promise<void>;
}
