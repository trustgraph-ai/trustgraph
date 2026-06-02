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
  makeFlowProcessor,
  makeConsumerSpec,
  type ProcessorConfig,
  type FlowProcessorRuntime,
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
  makeConsumerSpec<Triples, FalkorDBTriplesStoreError, FalkorDBTriplesStoreService>(
    "store-triples-input",
    onStoreTriplesMessage,
  ),
];

export type TriplesStoreService = FlowProcessorRuntime<FalkorDBTriplesStoreService>;

export function makeTriplesStoreService(config: ProcessorConfig): TriplesStoreService {
  const store = makeFalkorDBTriplesStoreService();
  const service = makeFlowProcessor(config, {
    specifications: makeTriplesStoreSpecs(),
    provide: (effect) =>
      effect.pipe(
        Effect.provideService(
          FalkorDBTriplesStoreService,
          FalkorDBTriplesStoreService.of(store),
        ),
      ),
  });
  void Effect.runPromise(Effect.log("[TriplesStore] Service initialized"));
  return service;
}

export const TriplesStoreService = makeTriplesStoreService;

export const program = makeFlowProcessorProgram<ProcessorConfig & FalkorDBConfig, never, FalkorDBTriplesStoreService>({
  id: "triples-store",
  specs: () => makeTriplesStoreSpecs(),
  layer: (config) => FalkorDBTriplesStoreLive(config),
});

export function run(): Promise<void> {
  return Effect.runPromise(program);
}
