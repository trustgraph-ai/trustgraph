/**
 * Graph RAG and Document RAG CLI commands.
 *
 * Python reference: trustgraph-cli/trustgraph/cli/invoke_graph_rag.py
 */

import { Effect } from "effect";
import * as O from "effect/Option";
import * as Argument from "effect/unstable/cli/Argument";
import * as Command from "effect/unstable/cli/Command";
import * as Flag from "effect/unstable/cli/Flag";
import { cliCommandError, withSocket, writeLine } from "./util.js";

export const graphRagCommand = Command.make("graph-rag", {
  query: Argument.string("query").pipe(Argument.withDescription("Natural language query")),
  entityLimit: Flag.integer("entity-limit").pipe(
    Flag.withDescription("Max entities"),
    Flag.withDefault(50),
  ),
  tripleLimit: Flag.integer("triple-limit").pipe(
    Flag.withDescription("Max triples per entity"),
    Flag.withDefault(30),
  ),
  collection: Flag.string("collection").pipe(
    Flag.withDescription("Collection name"),
    Flag.optional,
  ),
}, ({ query, entityLimit, tripleLimit, collection }) =>
  withSocket((socket, opts) =>
    Effect.gen(function* () {
        const flow = socket.flow(opts.flow);
      const response = yield* Effect.tryPromise({
        try: () =>
          flow.graphRag(
            query,
            {
              entityLimit,
              tripleLimit,
            },
            O.getOrUndefined(collection),
          ),
        catch: (error) => cliCommandError("graph-rag", error),
      });
      yield* writeLine(response);
    }),
  ),
).pipe(Command.withDescription("Query the knowledge graph using RAG"));

export const documentRagCommand = Command.make("document-rag", {
  query: Argument.string("query").pipe(Argument.withDescription("Natural language query")),
  docLimit: Flag.integer("doc-limit").pipe(
    Flag.withDescription("Max documents"),
    Flag.withDefault(20),
  ),
  collection: Flag.string("collection").pipe(
    Flag.withDescription("Collection name"),
    Flag.optional,
  ),
}, ({ query, docLimit, collection }) =>
  withSocket((socket, opts) =>
    Effect.gen(function* () {
        const flow = socket.flow(opts.flow);
      const response = yield* Effect.tryPromise({
        try: () =>
          flow.documentRag(
            query,
            docLimit,
            O.getOrUndefined(collection),
          ),
        catch: (error) => cliCommandError("document-rag", error),
      });
      yield* writeLine(response);
    }),
  ),
).pipe(Command.withDescription("Query documents using RAG"));
