/**
 * Effect Config contracts for process/runtime settings.
 *
 * These declarations preserve the existing environment variable names while
 * moving reads to a typed Effect boundary.
 */

import { Config, Effect } from "effect";
import * as O from "effect/Option";

export interface ProcessorRuntimeConfigOptions {
  readonly manageProcessSignals?: boolean;
}

export const optionalStringConfig = Effect.fn("optionalStringConfig")(function* (name: string) {
    return O.getOrUndefined(yield* Config.string(name).pipe(Config.option));
});

export const loadProcessorRuntimeConfig = Effect.fn("loadProcessorRuntimeConfig")(function* (
  id: string,
  options: ProcessorRuntimeConfigOptions = {},
) {
    const natsUrl = yield* optionalStringConfig("NATS_URL");
    const pulsarHost = yield* optionalStringConfig("PULSAR_HOST");
    const metricsPort = yield* Config.number("METRICS_PORT").pipe(Config.withDefault(8000));

    return {
      id,
      pubsubUrl: natsUrl ?? pulsarHost ?? "nats://localhost:4222",
      metricsPort,
      manageProcessSignals: options.manageProcessSignals ?? true,
    };
});
