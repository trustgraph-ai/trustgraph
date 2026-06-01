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
  type Spec,
} from "@trustgraph/base";
import { makeFlowProcessorProgram } from "@trustgraph/base";
import { Effect } from "effect";
import {
  FalkorDBTriplesStoreLive,
  FalkorDBTriplesStoreService,
  makeFalkorDBTriplesStoreService,
  type FalkorDBConfig,
  type FalkorDBTriplesStoreError,
} from "./falkordb.js";

const onStoreTriplesMessage = Effect.fn("TriplesStoreService.onMessage")(function* (
  msg: Triples,
  _properties: Record<string, string>,
  _flowCtx: FlowContext<FalkorDBTriplesStoreService>,
): Effect.fn.Return<void, FalkorDBTriplesStoreError, FalkorDBTriplesStoreService> {
  if (msg.triples.length === 0) return;

  const user = msg.metadata?.user ?? "default";
  const collection = msg.metadata?.collection ?? "default";
  const store = yield* FalkorDBTriplesStoreService;

  yield* store.storeTriples(msg.triples, user, collection);

  yield* Effect.log(
    `[TriplesStore] Stored ${msg.triples.length} triples for ${user}/${collection}`,
  );
});

export const makeTriplesStoreSpecs = (): ReadonlyArray<Spec<FalkorDBTriplesStoreService>> => [
  new ConsumerSpec<Triples, FalkorDBTriplesStoreError, FalkorDBTriplesStoreService>(
    "store-triples-input",
    onStoreTriplesMessage,
  ),
];

export class TriplesStoreService extends FlowProcessor<FalkorDBTriplesStoreService> {
  private readonly store = makeFalkorDBTriplesStoreService();

  constructor(config: ProcessorConfig) {
    super(config);

    for (const spec of makeTriplesStoreSpecs()) {
      this.registerSpecification(spec);
    }

    console.log("[TriplesStore] Service initialized");
  }

  override startEffect() {
    return super.startEffect().pipe(
      Effect.provideService(
        FalkorDBTriplesStoreService,
        FalkorDBTriplesStoreService.of(this.store),
      ),
    );
  }
}

export const program = makeFlowProcessorProgram<ProcessorConfig & FalkorDBConfig, never, FalkorDBTriplesStoreService>({
  id: "triples-store",
  specs: () => makeTriplesStoreSpecs(),
  layer: (config) => FalkorDBTriplesStoreLive(config),
});

export async function run(): Promise<void> {
  await Effect.runPromise(program);
}
