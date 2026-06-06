/**
 * Embeddings CLI commands.
 *
 * Generate text embeddings using the configured embedding model.
 */

import { Effect } from "effect";
import * as Argument from "effect/unstable/cli/Argument";
import * as Command from "effect/unstable/cli/Command";
import { cliCommandError, withSocket, writeJson } from "./util.js";

export const embeddingsCommand = Command.make("embeddings", {
  texts: Argument.string("text").pipe(
    Argument.withDescription("Text(s) to embed"),
    Argument.variadic({ min: 1 }),
  ),
}, ({ texts }) =>
  withSocket((socket, opts) =>
    Effect.gen(function* () {
        const flow = socket.flow(opts.flow);
      const vectors = yield* Effect.tryPromise({
        try: () => flow.embeddings(Array.from(texts)),
        catch: (error) => cliCommandError("embeddings", error),
      });
      yield* writeJson(vectors);
    }),
  ),
).pipe(Command.withDescription("Generate text embeddings"));
