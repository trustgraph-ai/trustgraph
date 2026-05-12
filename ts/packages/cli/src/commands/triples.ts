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
        const subject = cmdOpts.subject as string | undefined;
        const predicate = cmdOpts.predicate as string | undefined;
        const object = cmdOpts.object as string | undefined;
        const s: Term | undefined = subject !== undefined && subject.length > 0
          ? { t: "i", i: subject }
          : undefined;
        const p: Term | undefined = predicate !== undefined && predicate.length > 0
          ? { t: "i", i: predicate }
          : undefined;
        const o: Term | undefined = object !== undefined && object.length > 0
          ? { t: "i", i: object }
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
