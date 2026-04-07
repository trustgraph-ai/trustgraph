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
  type TriplesQueryRequest,
  type TriplesQueryResponse,
} from "@trustgraph/base";
import { FalkorDBTriplesQuery } from "./falkordb.js";

export class TriplesQueryService extends FlowProcessor {
  private query: FalkorDBTriplesQuery;

  constructor(config: ProcessorConfig) {
    super(config);
    this.query = new FalkorDBTriplesQuery();

    this.registerSpecification(
      new ConsumerSpec<TriplesQueryRequest>("triples-request", this.onMessage.bind(this)),
    );
    this.registerSpecification(new ProducerSpec<TriplesQueryResponse>("triples-response"));

    console.log("[TriplesQuery] Service initialized");
  }

  private async onMessage(
    msg: TriplesQueryRequest,
    properties: Record<string, string>,
    flowCtx: FlowContext,
  ): Promise<void> {
    const requestId = properties.id;
    if (!requestId) return;

    const producer = flowCtx.flow.producer<TriplesQueryResponse>("triples-response");

    try {
      const triples = await this.query.queryTriples(
        msg.s,
        msg.p,
        msg.o,
        msg.limit ?? 100,
      );

      await producer.send(requestId, { triples });
    } catch (err) {
      console.error("[TriplesQuery] Query failed:", err);
      await producer.send(requestId, {
        triples: [],
        error: { type: "query-error", message: String(err) },
      });
    }
  }
}

export async function run(): Promise<void> {
  await TriplesQueryService.launch("triples-query");
}
