/**
 * Parameter specification — declares a configuration parameter for a flow.
 *
 * Python reference: trustgraph-base/trustgraph/base/parameter_spec.py
 */

import { Effect, type Context } from "effect";
import * as S from "effect/Schema";
import type { PubSubBackend } from "../backend/types.js";
import type { SpecRuntimeRequirements } from "./types.js";
import type { Flow, FlowDefinition } from "../processor/flow.js";
import type { PubSubError } from "../errors.js";

declare const ParameterSpecType: unique symbol;

const UnknownParameterSchema: S.Codec<unknown, unknown> = S.Unknown;

export interface ParameterSpec<T = unknown> {
  readonly [ParameterSpecType]?: (_: T) => T;
  readonly name: string;
  readonly schema: S.Codec<T, unknown>;
  readonly addEffect: <Requirements = never>(
    flow: Flow<Requirements>,
    definition: FlowDefinition,
  ) => Effect.Effect<void, PubSubError, SpecRuntimeRequirements | Requirements>;
  readonly add: <Requirements = never>(
    flow: Flow<Requirements>,
    pubsub: PubSubBackend,
    definition: FlowDefinition,
    context: Context.Context<Requirements>,
  ) => Promise<void>;
}

export function makeParameterSpec(name: string): ParameterSpec<unknown>;
export function makeParameterSpec<T>(
  name: string,
  schema: S.Codec<T, unknown>,
): ParameterSpec<T>;
export function makeParameterSpec<T>(
  name: string,
  schema?: S.Codec<T, unknown>,
) {
  const parameterSchema = schema ?? UnknownParameterSchema;
  const addEffect = <Requirements = never>(flow: Flow<Requirements>, definition: FlowDefinition) =>
    Effect.sync(() => {
      const value = definition.parameters?.[name];
      flow.setParameter(name, value);
    });

  return {
    name,
    schema: parameterSchema,
    addEffect,
    add: <Requirements = never>(
      flow: Flow<Requirements>,
      pubsub: PubSubBackend,
      definition: FlowDefinition,
      context: Context.Context<Requirements>,
    ) =>
      flow.runInCompatibilityScope(addEffect(flow, definition), pubsub, context),
  };
}
