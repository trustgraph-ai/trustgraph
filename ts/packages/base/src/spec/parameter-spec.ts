/**
 * Parameter specification — declares a configuration parameter for a flow.
 *
 * Python reference: trustgraph-base/trustgraph/base/parameter_spec.py
 */

import { Effect, type Context } from "effect";
import * as S from "effect/Schema";
import type { PubSubBackend } from "../backend/types.js";
import type { Spec } from "./types.js";
import type { Flow, FlowDefinition } from "../processor/flow.js";

declare const ParameterSpecType: unique symbol;

const UnknownParameterSchema: S.Codec<unknown, unknown> = S.Unknown;

export interface ParameterSpec<T = unknown> extends Spec {
  readonly [ParameterSpecType]?: (_: T) => T;
  readonly schema: S.Codec<T, unknown>;
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
  const addEffect = (flow: Flow, definition: FlowDefinition) =>
    Effect.sync(() => {
      const value = definition.parameters?.[name];
      flow.setParameter(name, value);
    });

  return {
    name,
    schema: parameterSchema,
    addEffect,
    add: (
      flow: Flow,
      pubsub: PubSubBackend,
      definition: FlowDefinition,
      context: Context.Context<never>,
    ) =>
      flow.runInCompatibilityScope(addEffect(flow, definition), pubsub, context),
  };
}
