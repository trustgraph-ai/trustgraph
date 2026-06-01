/**
 * Triples query service — queries RDF triples from FalkorDB via FlowProcessor.
 *
 * Wraps FalkorDBTriplesQuery as a NATS consumer so the agent and Graph RAG
 * can query the knowledge graph over the message bus.
 *
 * Python reference: trustgraph-flow/trustgraph/query/triples/falkordb/service.py
 */

import {
  FlowProcessor,
  ConsumerSpec,
  ProducerSpec,
  type ProcessorConfig,
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
  new ConsumerSpec<
    TriplesQueryRequest,
    FlowResourceNotFoundError | MessagingDeliveryError,
    FalkorDBTriplesQueryService
  >("triples-request", onTriplesQueryMessage),
  new ProducerSpec<TriplesQueryResponse>("triples-response"),
];

export class TriplesQueryService extends FlowProcessor<FalkorDBTriplesQueryService> {
  private readonly query = makeFalkorDBTriplesQueryService();

  constructor(config: ProcessorConfig) {
    super(config);

    for (const spec of makeTriplesQuerySpecs()) {
      this.registerSpecification(spec);
    }

    console.log("[TriplesQuery] Service initialized");
  }

  override startEffect() {
    return super.startEffect().pipe(
      Effect.provideService(
        FalkorDBTriplesQueryService,
        FalkorDBTriplesQueryService.of(this.query),
      ),
    );
  }
}

export const program = makeFlowProcessorProgram<ProcessorConfig & FalkorDBQueryConfig, never, FalkorDBTriplesQueryService>({
  id: "triples-query",
  specs: () => makeTriplesQuerySpecs(),
  layer: (config) => FalkorDBTriplesQueryLive(config),
});

export async function run(): Promise<void> {
  await Effect.runPromise(program);
}
