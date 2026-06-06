/**
 * Triples query CLI commands.
 *
 * Query the knowledge graph for subject-predicate-object triples.
 */

import type { Term } from "@trustgraph/client";
import { Effect } from "effect";
import * as O from "effect/Option";
import * as Command from "effect/unstable/cli/Command";
import * as Flag from "effect/unstable/cli/Flag";
import { cliCommandError, withSocket, writeJson } from "./util.js";

export const triplesCommand = Command.make("triples", {
  subject: Flag.string("subject").pipe(
    Flag.withAlias("s"),
    Flag.withDescription("Subject IRI"),
    Flag.optional,
  ),
  predicate: Flag.string("predicate").pipe(
    Flag.withAlias("p"),
    Flag.withDescription("Predicate IRI"),
    Flag.optional,
  ),
  object: Flag.string("object").pipe(
    Flag.withAlias("o"),
    Flag.withDescription("Object IRI or literal"),
    Flag.optional,
  ),
  limit: Flag.integer("limit").pipe(
    Flag.withAlias("l"),
    Flag.withDescription("Max results"),
    Flag.withDefault(20),
  ),
  collection: Flag.string("collection").pipe(
    Flag.withDescription("Collection name"),
    Flag.optional,
  ),
}, ({ subject, predicate, object, limit, collection }) =>
  withSocket((socket, opts) =>
    Effect.gen(function* () {
        const flow = socket.flow(opts.flow);
      const subjectValue = O.getOrUndefined(subject);
      const predicateValue = O.getOrUndefined(predicate);
      const objectValue = O.getOrUndefined(object);
      const s: Term | undefined = subjectValue !== undefined && subjectValue.length > 0
          ? { t: "i", i: subjectValue }
          : undefined;
      const p: Term | undefined = predicateValue !== undefined && predicateValue.length > 0
          ? { t: "i", i: predicateValue }
          : undefined;
      const o: Term | undefined = objectValue !== undefined && objectValue.length > 0
          ? { t: "i", i: objectValue }
          : undefined;

      const triples = yield* Effect.tryPromise({
        try: () =>
          flow.triplesQuery(
            s,
            p,
            o,
            limit,
            O.getOrUndefined(collection),
          ),
        catch: (error) => cliCommandError("triples", error),
      });
      yield* writeJson(triples);
    }),
  ),
).pipe(Command.withDescription("Query knowledge graph triples"));
