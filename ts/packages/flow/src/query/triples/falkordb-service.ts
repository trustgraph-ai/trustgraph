/**
 * Triples query service — queries RDF triples from FalkorDB via FlowProcessor.
 *
 * Wraps FalkorDBTriplesQuery as a NATS consumer so the agent and Graph RAG
 * can query the knowledge graph over the message bus.
 *
 * Python reference: trustgraph-flow/trustgraph/query/triples/falkordb/service.py
 */

import {
  makeFlowProcessor,
  makeConsumerSpec,
  makeProducerSpec,
  type ProcessorConfig,
  type FlowProcessorRuntime,
  type FlowContext,
  type FlowResourceNotFoundError,
  type MessagingDeliveryError,
  type TriplesQueryRequest,
  type TriplesQueryResponse,
  type Spec,
} from "@trustgraph/base";
import { makeFlowProcessorProgram } from "@trustgraph/base";
import { Effect } from "effect";
import {
  FalkorDBTriplesQueryLive,
  FalkorDBTriplesQueryService,
  makeFalkorDBTriplesQueryService,
  type FalkorDBQueryConfig,
} from "./falkordb.js";

const onTriplesQueryMessage = Effect.fn("TriplesQueryService.onMessage")(function* (
  msg: TriplesQueryRequest,
  properties: Record<string, string>,
  flowCtx: FlowContext<FalkorDBTriplesQueryService>,
) {
  const requestId = properties.id;
  if (requestId === undefined || requestId.length === 0) return;

  const producer = yield* flowCtx.flow.producerEffect<TriplesQueryResponse>("triples-response");
  const query = yield* FalkorDBTriplesQueryService;
  const triples = yield* query.queryTriples(
    msg.s,
    msg.p,
    msg.o,
    msg.limit ?? 100,
  ).pipe(
    Effect.catch((error) =>
      Effect.logError("[TriplesQuery] Query failed", {
        error: error.message,
        operation: error.operation,
      }).pipe(
        Effect.flatMap(() =>
          producer.send(requestId, {
            triples: [],
            error: { type: "query-error", message: error.message },
          })
        ),
        Effect.as(null),
      ),
    ),
  );
  if (triples === null) return;

  yield* producer.send(requestId, { triples: Array.from(triples) });
});

export const makeTriplesQuerySpecs = (): ReadonlyArray<Spec<FalkorDBTriplesQueryService>> => [
  makeConsumerSpec<
    TriplesQueryRequest,
    FlowResourceNotFoundError | MessagingDeliveryError,
    FalkorDBTriplesQueryService
  >("triples-request", onTriplesQueryMessage),
  makeProducerSpec<TriplesQueryResponse>("triples-response"),
];

export type TriplesQueryService = FlowProcessorRuntime<FalkorDBTriplesQueryService>;

export function makeTriplesQueryService(config: ProcessorConfig): TriplesQueryService {
  const query = makeFalkorDBTriplesQueryService();
  const service = makeFlowProcessor(config, {
    specifications: makeTriplesQuerySpecs(),
    provide: (effect) =>
      effect.pipe(
        Effect.provideService(
          FalkorDBTriplesQueryService,
          FalkorDBTriplesQueryService.of(query),
        ),
      ),
  });
  console.log("[TriplesQuery] Service initialized");
  return service;
}

export const TriplesQueryService = makeTriplesQueryService;

export const program = makeFlowProcessorProgram<ProcessorConfig & FalkorDBQueryConfig, never, FalkorDBTriplesQueryService>({
  id: "triples-query",
  specs: () => makeTriplesQuerySpecs(),
  layer: (config) => FalkorDBTriplesQueryLive(config),
});

export async function run(): Promise<void> {
  await Effect.runPromise(program);
}
