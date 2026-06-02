/**
 * Graph RAG and Document RAG CLI commands.
 *
 * Python reference: trustgraph-cli/trustgraph/cli/invoke_graph_rag.py
 */

import type { Command } from "commander";
import { Effect } from "effect";
import { cliCommandError, withSocket, writeLine } from "./util.js";

export function registerGraphRagCommands(program: Command): void {
  program
    .command("graph-rag")
    .description("Query the knowledge graph using RAG")
    .argument("<query>", "Natural language query")
    .option("--entity-limit <n>", "Max entities", "50")
    .option("--triple-limit <n>", "Max triples per entity", "30")
    .option("--collection <name>", "Collection name")
    .action((query: string, cmdOpts, cmd) =>
      Effect.runPromise(withSocket(cmd, (socket, opts) =>
        Effect.gen(function* () {
        const flow = socket.flow(opts.flow);
        const collection = cmdOpts.collection as string | undefined;
          const response = yield* Effect.tryPromise({
            try: () =>
              flow.graphRag(
                query,
                {
                  entityLimit: parseInt(cmdOpts.entityLimit, 10),
                  tripleLimit: parseInt(cmdOpts.tripleLimit, 10),
                },
                collection,
              ),
            catch: (error) => cliCommandError("graph-rag", error),
          });
          yield* writeLine(response);
        }),
      )),
    );

  program
    .command("document-rag")
    .description("Query documents using RAG")
    .argument("<query>", "Natural language query")
    .option("--doc-limit <n>", "Max documents", "20")
    .option("--collection <name>", "Collection name")
    .action((query: string, cmdOpts, cmd) =>
      Effect.runPromise(withSocket(cmd, (socket, opts) =>
        Effect.gen(function* () {
        const flow = socket.flow(opts.flow);
        const docLimit = cmdOpts.docLimit as string | undefined;
        const collection = cmdOpts.collection as string | undefined;
          const response = yield* Effect.tryPromise({
            try: () =>
              flow.documentRag(
                query,
                docLimit !== undefined && docLimit.length > 0
                  ? parseInt(docLimit, 10)
                  : undefined,
                collection,
              ),
            catch: (error) => cliCommandError("document-rag", error),
          });
          yield* writeLine(response);
        }),
      )),
    );
}
