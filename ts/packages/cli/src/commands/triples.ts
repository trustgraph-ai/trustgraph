/**
 * Triples query CLI commands.
 *
 * Query the knowledge graph for subject-predicate-object triples.
 */

import type { Command } from "commander";
import type { Term } from "@trustgraph/client";
import { createSocket, getOpts } from "./util.js";

export function registerTriplesCommands(program: Command): void {
  program
    .command("triples")
    .description("Query knowledge graph triples")
    .option("-s, --subject <iri>", "Subject IRI")
    .option("-p, --predicate <iri>", "Predicate IRI")
    .option("-o, --object <iri>", "Object IRI or literal")
    .option("-l, --limit <n>", "Max results", "20")
    .option("--collection <name>", "Collection name")
    .action(async (cmdOpts, cmd) => {
      const opts = getOpts(cmd);
      const socket = await createSocket(opts);

      try {
        const flow = socket.flow(opts.flow);
        const s: Term | undefined = cmdOpts.subject
          ? { t: "i", i: cmdOpts.subject as string }
          : undefined;
        const p: Term | undefined = cmdOpts.predicate
          ? { t: "i", i: cmdOpts.predicate as string }
          : undefined;
        const o: Term | undefined = cmdOpts.object
          ? { t: "i", i: cmdOpts.object as string }
          : undefined;

        const triples = await flow.triplesQuery(
          s,
          p,
          o,
          parseInt(cmdOpts.limit as string, 10),
          cmdOpts.collection as string | undefined,
        );
        console.log(JSON.stringify(triples, null, 2));
      } finally {
        socket.close();
      }
    });
}
