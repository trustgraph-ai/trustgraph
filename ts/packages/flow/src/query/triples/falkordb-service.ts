/**
 * Triples query service — queries RDF triples from FalkorDB via FlowProcessor.
 *
 * Wraps FalkorDBTriplesQuery as a NATS consumer so the agent and Graph RAG
 * can query the knowledge graph over the message bus.
 *
 * Python reference: trustgraph-flow/trustgraph/query/triples/falkordb/service.py
 */

import type {
  ProcessorConfig,
  FlowProcessorRuntime,
  FlowProcessorStartEffect,
  FlowContext,
  FlowResourceNotFoundError,
  MessagingDeliveryError,
  TriplesQueryRequest,
  TriplesQueryResponse,
  Spec,
} from "@trustgraph/base";
import {
  makeFlowProcessor,
  makeConsumerSpec,
  makeProducerSpec,
  processorLifecycleError,
} from "@trustgraph/base";
import { NodeRuntime } from "@effect/platform-node";
import { makeFlowProcessorProgram } from "@trustgraph/base";
import { Effect } from "effect";
import type {
  FalkorDBQueryConfig,
  FalkorDBTriplesQueryError,
} from "./falkordb.js";
import {
  FalkorDBTriplesQueryLive,
  FalkorDBTriplesQueryService,
  makeFalkorDBTriplesQueryServiceScoped,
} from "./falkordb.js";

const TriplesResponseProducer = makeProducerSpec<TriplesQueryResponse>("triples-response");

const onTriplesQueryMessage = Effect.fn("TriplesQueryService.onMessage")(function* (
  msg: TriplesQueryRequest,
  properties: Record<string, string>,
  flowCtx: FlowContext<FalkorDBTriplesQueryService>,
) {
  const requestId = properties.id;
  if (requestId === undefined || requestId.length === 0) return;

  const producer = yield* flowCtx.flow.producerEffect(TriplesResponseProducer);
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
  TriplesResponseProducer,
];

export type TriplesQueryService = FlowProcessorRuntime<FalkorDBTriplesQueryService>;

const provideFalkorDBTriplesQuery = (processorId: string) =>
  Effect.fn("TriplesQueryService.provideFalkorDB")(function* (
    effect: FlowProcessorStartEffect<FalkorDBTriplesQueryService>,
  ) {
    const query = yield* makeFalkorDBTriplesQueryServiceScoped().pipe(
      Effect.mapError((error) => processorLifecycleError(processorId, "falkordb-query-connect", error)),
    );
    yield* effect.pipe(
      Effect.provideService(
        FalkorDBTriplesQueryService,
        FalkorDBTriplesQueryService.of(query),
      ),
    );
  });

export function makeTriplesQueryService(config: ProcessorConfig): TriplesQueryService {
  return makeFlowProcessor(config, {
    specifications: makeTriplesQuerySpecs(),
    provide: provideFalkorDBTriplesQuery(config.id),
  });
}

export const TriplesQueryService = makeTriplesQueryService;

export const program = makeFlowProcessorProgram<
  ProcessorConfig & FalkorDBQueryConfig,
  FalkorDBTriplesQueryError,
  FalkorDBTriplesQueryService
>({
  id: "triples-query",
  specs: () => makeTriplesQuerySpecs(),
  layer: (config) => FalkorDBTriplesQueryLive(config),
});

export function runMain(): void {
  NodeRuntime.runMain(program);
}
