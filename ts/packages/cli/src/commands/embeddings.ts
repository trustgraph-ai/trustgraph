/**
 * Embeddings CLI commands.
 *
 * Generate text embeddings using the configured embedding model.
 */

import type { Command } from "commander";
import { Effect } from "effect";
import { cliCommandError, withSocket, writeJson } from "./util.js";

export function registerEmbeddingsCommands(program: Command): void {
  program
    .command("embeddings")
    .description("Generate text embeddings")
    .argument("<text...>", "Text(s) to embed")
    .action((texts: string[], _opts, cmd) =>
      Effect.runPromise(withSocket(cmd, (socket, opts) =>
        Effect.gen(function* () {
        const flow = socket.flow(opts.flow);
          const vectors = yield* Effect.tryPromise({
            try: () => flow.embeddings(texts),
            catch: (error) => cliCommandError("embeddings", error),
          });
          yield* writeJson(vectors);
        }),
      )),
    );
}
