/**
 * Document library CLI commands.
 *
 * Manages documents stored in the TrustGraph library.
 */

import type { Command } from "commander";
import { createSocket, getOpts } from "./util.js";

function basenamePath(filepath: string): string {
  const normalized = filepath.replace(/\/+$/, "");
  const index = normalized.lastIndexOf("/");
  return index >= 0 ? normalized.slice(index + 1) : normalized;
}

/** Simple MIME-type lookup by file extension. */
function guessMimeType(filepath: string): string {
  const ext = filepath.split(".").pop()?.toLowerCase();
  switch (ext) {
    case "pdf":
      return "application/pdf";
    case "txt":
      return "text/plain";
    case "md":
      return "text/markdown";
    case "html":
    case "htm":
      return "text/html";
    case "json":
      return "application/json";
    case "csv":
      return "text/csv";
    case "docx":
      return "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
    default:
      return "application/octet-stream";
  }
}

export function registerLibraryCommands(program: Command): void {
  const library = program
    .command("library")
    .description("Document library management");

  library
    .command("list")
    .description("List documents in the library")
    .action(async (_opts, cmd) => {
      const opts = getOpts(cmd);
      const socket = await createSocket(opts);

      try {
        const lib = socket.librarian();
        const docs = await lib.getDocuments();
        console.log(JSON.stringify(docs, null, 2));
      } finally {
        socket.close();
      }
    });

  library
    .command("load")
    .description("Load a document into the library")
    .argument("<file>", "Path to the file to load")
    .option("-t, --title <title>", "Document title")
    .option("-m, --mime-type <type>", "MIME type (auto-detected if omitted)")
    .option("-c, --comments <text>", "Comments", "")
    .option("--tags <tags...>", "Document tags")
    .option("--id <id>", "Optional document ID")
    .action(async (file: string, cmdOpts, cmd) => {
      const opts = getOpts(cmd);
      const socket = await createSocket(opts);

      try {
        const lib = socket.librarian();
        const data = new Uint8Array(await Bun.file(file).arrayBuffer());
        const b64 = Buffer.from(data).toString("base64");
        const mimeType = (cmdOpts.mimeType as string | undefined) ?? guessMimeType(file);
        const title = (cmdOpts.title as string | undefined) ?? basenamePath(file);
        const comments = cmdOpts.comments as string;
        const tags: string[] = (cmdOpts.tags as string[] | undefined) ?? [];

        const resp = await lib.loadDocument(
          b64,
          mimeType,
          title,
          comments,
          tags,
          cmdOpts.id as string | undefined,
        );
        console.log(JSON.stringify(resp, null, 2));
      } finally {
        socket.close();
      }
    });

  library
    .command("remove")
    .description("Remove a document from the library")
    .argument("<id>", "Document ID to remove")
    .option("--collection <name>", "Collection name")
    .action(async (id: string, cmdOpts, cmd) => {
      const opts = getOpts(cmd);
      const socket = await createSocket(opts);

      try {
        const lib = socket.librarian();
        const resp = await lib.removeDocument(id, cmdOpts.collection as string | undefined);
        console.log(JSON.stringify(resp, null, 2));
      } finally {
        socket.close();
      }
    });

  library
    .command("processing")
    .description("List documents currently being processed")
    .action(async (_opts, cmd) => {
      const opts = getOpts(cmd);
      const socket = await createSocket(opts);

      try {
        const lib = socket.librarian();
        const items = await lib.getProcessing();
        console.log(JSON.stringify(items, null, 2));
      } finally {
        socket.close();
      }
    });
}
