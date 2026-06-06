/**
 * Document library CLI commands.
 *
 * Manages documents stored in the TrustGraph library.
 */

import { Effect, Match } from "effect";
import * as O from "effect/Option";
import * as Argument from "effect/unstable/cli/Argument";
import * as Command from "effect/unstable/cli/Command";
import * as Flag from "effect/unstable/cli/Flag";
import { cliCommandError, withSocket, writeJson } from "./util.js";

function basenamePath(filepath: string): string {
  const normalized = filepath.replace(/\/+$/, "");
  const index = normalized.lastIndexOf("/");
  return index >= 0 ? normalized.slice(index + 1) : normalized;
}

/** Simple MIME-type lookup by file extension. */
export function guessMimeType(filepath: string): string {
  const ext = filepath.split(".").pop()?.toLowerCase();
  return Match.value(ext).pipe(
    Match.when("pdf", () => "application/pdf"),
    Match.when("txt", () => "text/plain"),
    Match.when("md", () => "text/markdown"),
    Match.when("html", () => "text/html"),
    Match.when("htm", () => "text/html"),
    Match.when("json", () => "application/json"),
    Match.when("csv", () => "text/csv"),
    Match.when("docx", () => "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    Match.orElse(() => "application/octet-stream"),
  );
}

const list = Command.make("list", {}, () =>
  withSocket((socket) =>
    Effect.gen(function* () {
        const lib = socket.librarian();
      const docs = yield* Effect.tryPromise({
        try: () => lib.getDocuments(),
        catch: (error) => cliCommandError("library.list", error),
      });
      yield* writeJson(docs);
    }),
  ),
).pipe(Command.withDescription("List documents in the library"));

const load = Command.make("load", {
  file: Argument.string("file").pipe(Argument.withDescription("Path to the file to load")),
  title: Flag.string("title").pipe(
    Flag.withAlias("t"),
    Flag.withDescription("Document title"),
    Flag.optional,
  ),
  mimeType: Flag.string("mime-type").pipe(
    Flag.withAlias("m"),
    Flag.withDescription("MIME type (auto-detected if omitted)"),
    Flag.optional,
  ),
  comments: Flag.string("comments").pipe(
    Flag.withAlias("c"),
    Flag.withDescription("Comments"),
    Flag.withDefault(""),
  ),
  tags: Flag.string("tags").pipe(
    Flag.withDescription("Document tags"),
    Flag.atMost(Number.MAX_SAFE_INTEGER),
  ),
  id: Flag.string("id").pipe(
    Flag.withDescription("Optional document ID"),
    Flag.optional,
  ),
}, ({ file, title, mimeType, comments, tags, id }) =>
  withSocket((socket) =>
    Effect.gen(function* () {
        const lib = socket.librarian();
      const data = new Uint8Array(yield* Effect.tryPromise({
        try: () => Bun.file(file).arrayBuffer(),
        catch: (error) => cliCommandError("library.load.read-file", error),
      }));
      const b64 = Buffer.from(data).toString("base64");
      const resolvedMimeType = O.getOrUndefined(mimeType) ?? guessMimeType(file);
      const resolvedTitle = O.getOrUndefined(title) ?? basenamePath(file);

      const resp = yield* Effect.tryPromise({
        try: () =>
          lib.loadDocument(
            b64,
            resolvedMimeType,
            resolvedTitle,
            comments,
            Array.from(tags),
            O.getOrUndefined(id),
          ),
        catch: (error) => cliCommandError("library.load", error),
      });
      yield* writeJson(resp);
    }),
  ),
).pipe(Command.withDescription("Load a document into the library"));

const remove = Command.make("remove", {
  id: Argument.string("id").pipe(Argument.withDescription("Document ID to remove")),
  collection: Flag.string("collection").pipe(
    Flag.withDescription("Collection name"),
    Flag.optional,
  ),
}, ({ id, collection }) =>
  withSocket((socket) =>
    Effect.gen(function* () {
        const lib = socket.librarian();
      const resp = yield* Effect.tryPromise({
        try: () => lib.removeDocument(id, O.getOrUndefined(collection)),
        catch: (error) => cliCommandError("library.remove", error),
      });
      yield* writeJson(resp);
    }),
  ),
).pipe(Command.withDescription("Remove a document from the library"));

const processing = Command.make("processing", {}, () =>
  withSocket((socket) =>
    Effect.gen(function* () {
        const lib = socket.librarian();
      const items = yield* Effect.tryPromise({
        try: () => lib.getProcessing(),
        catch: (error) => cliCommandError("library.processing", error),
      });
      yield* writeJson(items);
    }),
  ),
).pipe(Command.withDescription("List documents currently being processed"));

export const libraryCommand = Command.make("library").pipe(
  Command.withDescription("Document library management"),
  Command.withSubcommands([list, load, remove, processing]),
);
