/**
 * Triples store service — writes RDF triples to FalkorDB via FlowProcessor.
 *
 * A FlowProcessor that:
 * 1. Consumes Triples messages
 * 2. Writes each triple to FalkorDB using FalkorDBTriplesStore
 *
 * Python reference: trustgraph-flow/trustgraph/storage/triples/falkordb/service.py
 */

import {
  FlowProcessor,
  ConsumerSpec,
  type ProcessorConfig,
  type FlowContext,
  type Triples,
} from "@trustgraph/base";
import { FalkorDBTriplesStore } from "./falkordb.js";

export class TriplesStoreService extends FlowProcessor {
  private store: FalkorDBTriplesStore;

  constructor(config: ProcessorConfig) {
    super(config);
    this.store = new FalkorDBTriplesStore();

    this.registerSpecification(
      new ConsumerSpec<Triples>("store-triples-input", this.onMessage.bind(this)),
    );

    console.log("[TriplesStore] Service initialized");
  }

  private async onMessage(
    msg: Triples,
    properties: Record<string, string>,
    flowCtx: FlowContext,
  ): Promise<void> {
    if (!msg.triples || msg.triples.length === 0) return;

    const user = msg.metadata?.user ?? "default";
    const collection = msg.metadata?.collection ?? "default";

    await this.store.storeTriples(msg.triples, user, collection);

    console.log(
      `[TriplesStore] Stored ${msg.triples.length} triples for ${user}/${collection}`,
    );
  }
}

export async function run(): Promise<void> {
  await TriplesStoreService.launch("triples-store");
}
