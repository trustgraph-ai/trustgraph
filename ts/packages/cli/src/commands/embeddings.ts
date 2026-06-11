/**
 * Embeddings CLI commands.
 *
 * Generate text embeddings using the configured embedding model.
 */

import { Effect } from "effect";
import * as Argument from "effect/unstable/cli/Argument";
import * as Command from "effect/unstable/cli/Command";
import { gatewayDispatch, withGatewayClient, writeJson } from "./util.js";

export const embeddingsCommand = Command.make("embeddings", {
  texts: Argument.string("text").pipe(
    Argument.withDescription("Text(s) to embed"),
    Argument.variadic({ min: 1 }),
  ),
}, ({ texts }) =>
  withGatewayClient((client, opts) =>
    Effect.gen(function* () {
      const response = yield* gatewayDispatch(client, "embeddings", "embeddings", {
        texts: Array.from(texts),
      }, { flow: opts.flow, timeoutMs: 30000 });
      const record = response as Record<string, unknown>;
      yield* writeJson(record.vectors ?? []);
    }),
  ),
).pipe(Command.withDescription("Generate text embeddings"));
