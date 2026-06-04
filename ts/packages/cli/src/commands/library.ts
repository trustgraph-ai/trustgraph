/**
 * Document library CLI commands.
 *
 * Manages documents stored in the TrustGraph library.
 */

import type { Command } from "commander";
import { Effect, Match } from "effect";
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

export function registerLibraryCommands(program: Command): void {
  const library = program
    .command("library")
    .description("Document library management");

  library
    .command("list")
    .description("List documents in the library")
    .action((_opts, cmd) =>
      Effect.runPromise(withSocket(cmd, (socket) =>
        Effect.gen(function* () {
        const lib = socket.librarian();
          const docs = yield* Effect.tryPromise({
            try: () => lib.getDocuments(),
            catch: (error) => cliCommandError("library.list", error),
          });
          yield* writeJson(docs);
        }),
      )),
    );

  library
    .command("load")
    .description("Load a document into the library")
    .argument("<file>", "Path to the file to load")
    .option("-t, --title <title>", "Document title")
    .option("-m, --mime-type <type>", "MIME type (auto-detected if omitted)")
    .option("-c, --comments <text>", "Comments", "")
    .option("--tags <tags...>", "Document tags")
    .option("--id <id>", "Optional document ID")
    .action((file: string, cmdOpts, cmd) =>
      Effect.runPromise(withSocket(cmd, (socket) =>
        Effect.gen(function* () {
        const lib = socket.librarian();
          const data = new Uint8Array(yield* Effect.tryPromise({
            try: () => Bun.file(file).arrayBuffer(),
            catch: (error) => cliCommandError("library.load.read-file", error),
          }));
        const b64 = Buffer.from(data).toString("base64");
        const mimeType = (cmdOpts.mimeType as string | undefined) ?? guessMimeType(file);
        const title = (cmdOpts.title as string | undefined) ?? basenamePath(file);
        const comments = cmdOpts.comments as string;
        const tags: string[] = (cmdOpts.tags as string[] | undefined) ?? [];

          const resp = yield* Effect.tryPromise({
            try: () =>
              lib.loadDocument(
                b64,
                mimeType,
                title,
                comments,
                tags,
                cmdOpts.id as string | undefined,
              ),
            catch: (error) => cliCommandError("library.load", error),
          });
          yield* writeJson(resp);
        }),
      )),
    );

  library
    .command("remove")
    .description("Remove a document from the library")
    .argument("<id>", "Document ID to remove")
    .option("--collection <name>", "Collection name")
    .action((id: string, cmdOpts, cmd) =>
      Effect.runPromise(withSocket(cmd, (socket) =>
        Effect.gen(function* () {
        const lib = socket.librarian();
          const resp = yield* Effect.tryPromise({
            try: () => lib.removeDocument(id, cmdOpts.collection as string | undefined),
            catch: (error) => cliCommandError("library.remove", error),
          });
          yield* writeJson(resp);
        }),
      )),
    );

  library
    .command("processing")
    .description("List documents currently being processed")
    .action((_opts, cmd) =>
      Effect.runPromise(withSocket(cmd, (socket) =>
        Effect.gen(function* () {
        const lib = socket.librarian();
          const items = yield* Effect.tryPromise({
            try: () => lib.getProcessing(),
            catch: (error) => cliCommandError("library.processing", error),
          });
          yield* writeJson(items);
        }),
      )),
    );
}
