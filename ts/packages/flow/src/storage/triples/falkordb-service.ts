/**
 * Triples store service — writes RDF triples to FalkorDB via FlowProcessor.
 *
 * A FlowProcessor that:
 * 1. Consumes Triples messages
 * 2. Writes each triple to FalkorDB using FalkorDBTriplesStore
 *
 * Python reference: trustgraph-flow/trustgraph/storage/triples/falkordb/service.py
 */

import type {
  ProcessorConfig,
  FlowProcessorRuntime,
  FlowProcessorStartEffect,
  FlowContext,
  Triples,
  Spec,
} from "@trustgraph/base";
import {
  makeFlowProcessor,
  makeConsumerSpec,
  processorLifecycleError,
} from "@trustgraph/base";
import { NodeRuntime } from "@effect/platform-node";
import { makeFlowProcessorProgram } from "@trustgraph/base";
import { Effect } from "effect";
import type {
  FalkorDBConfig,
  FalkorDBTriplesStoreError,
} from "./falkordb.js";
import {
  FalkorDBTriplesStoreLive,
  FalkorDBTriplesStoreService,
  makeFalkorDBTriplesStoreServiceScoped,
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

const provideFalkorDBTriplesStore = (processorId: string) =>
  Effect.fn("TriplesStoreService.provideFalkorDB")(function* (
    effect: FlowProcessorStartEffect<FalkorDBTriplesStoreService>,
  ) {
    const store = yield* makeFalkorDBTriplesStoreServiceScoped().pipe(
      Effect.mapError((error) => processorLifecycleError(processorId, "falkordb-store-connect", error)),
    );
    yield* effect.pipe(
      Effect.provideService(
        FalkorDBTriplesStoreService,
        FalkorDBTriplesStoreService.of(store),
      ),
    );
  });

export function makeTriplesStoreService(config: ProcessorConfig): TriplesStoreService {
  return makeFlowProcessor(config, {
    specifications: makeTriplesStoreSpecs(),
    provide: provideFalkorDBTriplesStore(config.id),
  });
}

export const TriplesStoreService = makeTriplesStoreService;

export const program = makeFlowProcessorProgram<
  ProcessorConfig & FalkorDBConfig,
  FalkorDBTriplesStoreError,
  FalkorDBTriplesStoreService
>({
  id: "triples-store",
  specs: () => makeTriplesStoreSpecs(),
  layer: (config) => FalkorDBTriplesStoreLive(config),
});

export function runMain(): void {
  NodeRuntime.runMain(program);
}
