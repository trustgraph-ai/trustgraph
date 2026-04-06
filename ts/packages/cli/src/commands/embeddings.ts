/**
 * Embeddings CLI commands.
 *
 * Generate text embeddings using the configured embedding model.
 */

import type { Command } from "commander";
import { createSocket, getOpts } from "./util.js";

export function registerEmbeddingsCommands(program: Command): void {
  program
    .command("embeddings")
    .description("Generate text embeddings")
    .argument("<text...>", "Text(s) to embed")
    .action(async (texts: string[], _opts, cmd) => {
      const opts = getOpts(cmd);
      const socket = await createSocket(opts);

      try {
        const flow = socket.flow(opts.flow);
        const vectors = await flow.embeddings(texts);
        console.log(JSON.stringify(vectors, null, 2));
      } finally {
        socket.close();
      }
    });
}
