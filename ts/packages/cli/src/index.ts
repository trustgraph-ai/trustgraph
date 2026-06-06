#!/usr/bin/env node

/** @effect-diagnostics strictEffectProvide:skip-file */

/**
 * Unified TrustGraph CLI.
 *
 * Replaces the 60+ individual Python CLI scripts with a single
 * `tg` command using subcommands.
 *
 * Python reference: trustgraph-cli/trustgraph/cli/
 */

import { BunRuntime, BunServices } from "@effect/platform-bun";
import { Effect } from "effect";
import * as Command from "effect/unstable/cli/Command";
import { agentCommand } from "./commands/agent.js";
import { configCommand } from "./commands/config.js";
import { embeddingsCommand } from "./commands/embeddings.js";
import { flowCommand } from "./commands/flow.js";
import { graphRagCommand, documentRagCommand } from "./commands/graph-rag.js";
import { libraryCommand } from "./commands/library.js";
import { triplesCommand } from "./commands/triples.js";
import { rootCommand } from "./commands/util.js";

export const cli = rootCommand.pipe(
  Command.withSubcommands([
    agentCommand,
    graphRagCommand,
    documentRagCommand,
    configCommand,
    flowCommand,
    libraryCommand,
    triplesCommand,
    embeddingsCommand,
  ]),
);

export const program = Command.run(cli, { version: "0.1.0" }).pipe(
  Effect.provide(BunServices.layer),
);

BunRuntime.runMain(program);
