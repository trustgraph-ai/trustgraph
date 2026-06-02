/**
 * Graph RAG retrieval pipeline.
 *
 * Python reference: trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py
 */

import type {
  EmbeddingsRequest,
  EmbeddingsResponse,
  EffectRequestOptions,
  EffectRequestResponse,
  GraphEmbeddingsRequest,
  GraphEmbeddingsResponse,
  PromptRequest,
  PromptResponse,
  Term,
  TextCompletionRequest,
  TextCompletionResponse,
  Triple,
  TriplesQueryRequest,
  TriplesQueryResponse,
} from "@trustgraph/base";
import { errorMessage } from "@trustgraph/base";
import { Context, Effect, Layer } from "effect";
import * as O from "effect/Option";
import * as S from "effect/Schema";

export interface GraphRagConfig {
  entityLimit?: number;
  tripleLimit?: number;
  maxSubgraphSize?: number;
  maxPathLength?: number;
  edgeScoreLimit?: number;
  edgeLimit?: number;
}

export interface GraphRagClients {
  llm: EffectRequestResponse<TextCompletionRequest, TextCompletionResponse>;
  embeddings: EffectRequestResponse<EmbeddingsRequest, EmbeddingsResponse>;
  graphEmbeddings: EffectRequestResponse<GraphEmbeddingsRequest, GraphEmbeddingsResponse>;
  triples: EffectRequestResponse<TriplesQueryRequest, TriplesQueryResponse>;
  prompt: EffectRequestResponse<PromptRequest, PromptResponse>;
}

export type ChunkCallback = (text: string, endOfStream: boolean) => Promise<void>;

export interface GraphRagQueryOptions {
  readonly collection?: string;
  readonly streaming?: boolean;
  readonly chunkCallback?: ChunkCallback;
}

export interface GraphRagResult {
  answer: string;
  subgraph: Triple[];
}

interface NormalizedGraphRagConfig {
  entityLimit: number;
  tripleLimit: number;
  maxSubgraphSize: number;
  maxPathLength: number;
  edgeScoreLimit: number;
  edgeLimit: number;
}

export class GraphRagEngineError extends S.TaggedErrorClass<GraphRagEngineError>()(
  "GraphRagEngineError",
  {
    message: S.String,
    operation: S.String,
    cause: S.DefectWithStack,
  },
) {}

export interface GraphRagEngineShape {
  readonly query: (
    clients: GraphRagClients,
    queryText: string,
    options?: GraphRagQueryOptions,
    config?: GraphRagConfig,
  ) => Effect.Effect<GraphRagResult, GraphRagEngineError>;
}

export class GraphRagEngine extends Context.Service<GraphRagEngine, GraphRagEngineShape>()(
  "@trustgraph/flow/retrieval/graph-rag/GraphRagEngine",
) {}

const graphRagError = (operation: string, cause: unknown) =>
  GraphRagEngineError.make({
    operation,
    cause,
    message: errorMessage(cause),
  });

const requestClient = <TReq, TRes>(
  requestor: EffectRequestResponse<TReq, TRes>,
  operation: string,
  request: TReq,
  options?: EffectRequestOptions<TRes, GraphRagEngineError>,
): Effect.Effect<TRes, GraphRagEngineError> =>
  requestor.request(request, options).pipe(
    Effect.mapError((cause) => graphRagError(operation, cause)),
  );

export function normalizeGraphRagConfig(config: GraphRagConfig = {}): NormalizedGraphRagConfig {
  return {
    entityLimit: config.entityLimit ?? 50,
    tripleLimit: config.tripleLimit ?? 30,
    maxSubgraphSize: config.maxSubgraphSize ?? 1000,
    maxPathLength: config.maxPathLength ?? 2,
    edgeScoreLimit: config.edgeScoreLimit ?? 50,
    edgeLimit: config.edgeLimit ?? 25,
  };
}

export function makeGraphRagEngine(): GraphRagEngineShape {
  return {
    query: Effect.fn("GraphRagEngine.query")((
      clients: GraphRagClients,
      queryText: string,
      options?: GraphRagQueryOptions,
      config?: GraphRagConfig,
    ) => queryGraphRag(clients, queryText, options, config),
    ),
  };
}

export const GraphRagLive: Layer.Layer<GraphRagEngine> = Layer.succeed(
  GraphRagEngine,
  GraphRagEngine.of(makeGraphRagEngine()),
);

export interface GraphRag {
  readonly query: (
    queryText: string,
    options?: GraphRagQueryOptions,
  ) => Promise<GraphRagResult>;
}

export function makeGraphRag(
  clients: GraphRagClients,
  config: GraphRagConfig = {},
): GraphRag {
  const engine = makeGraphRagEngine();
  return {
    query: (queryText, options) =>
      Effect.runPromise(engine.query(clients, queryText, options, config)),
  };
}

function queryGraphRag(
  clients: GraphRagClients,
  queryText: string,
  options?: GraphRagQueryOptions,
  rawConfig?: GraphRagConfig,
): Effect.Effect<GraphRagResult, GraphRagEngineError> {
  return Effect.gen(function* () {
    const config = normalizeGraphRagConfig(rawConfig);
    yield* Effect.log(`[GraphRag] Query: "${queryText.slice(0, 80)}..."`);

    const concepts = yield* extractConcepts(clients, queryText);
    yield* Effect.log(`[GraphRag] Step 1: extracted ${concepts.length} concepts: ${concepts.slice(0, 5).join(", ")}`);

    const vectors = yield* getVectors(clients, concepts);
    yield* Effect.log(`[GraphRag] Step 2: got ${vectors.length} vectors (dim=${vectors[0]?.length ?? 0})`);

    const entities = yield* getEntities(clients, config, vectors, options?.collection);
    yield* Effect.log(`[GraphRag] Step 3: found ${entities.length} matching entities`);

    const subgraph = yield* followEdges(clients, config, entities, options?.collection);
    yield* Effect.log(`[GraphRag] Step 4: traversed graph, ${subgraph.length} triples in subgraph`);

    const scoredEdges = yield* scoreEdges(clients, config, queryText, subgraph);
    yield* Effect.log(`[GraphRag] Step 5: scored down to ${scoredEdges.length} edges`);

    yield* Effect.log(`[GraphRag] Step 6: synthesizing answer from ${scoredEdges.length} edges...`);
    const answer = yield* synthesize(
      clients,
      queryText,
      scoredEdges,
      options?.chunkCallback,
    );
    yield* Effect.log(`[GraphRag] Step 6: done (${answer.length} chars)`);

    return { answer, subgraph: scoredEdges };
  });
}

function extractConcepts(clients: GraphRagClients, query: string): Effect.Effect<string[], GraphRagEngineError> {
  return Effect.gen(function* () {
    const promptResp = yield* requestClient(
      clients.prompt,
      "extract-concepts-prompt",
      {
        name: "extract-concepts",
        variables: { query },
      },
    );

    const llmResp = yield* requestClient(
      clients.llm,
      "extract-concepts-llm",
      {
        system: promptResp.system,
        prompt: promptResp.prompt,
      },
    );

    return llmResp.response
      .split("\n")
      .map((concept) => concept.trim())
      .filter((concept) => concept.length > 0);
  });
}

function getVectors(clients: GraphRagClients, concepts: string[]): Effect.Effect<number[][], GraphRagEngineError> {
  return Effect.gen(function* () {
    const resp = yield* requestClient(clients.embeddings, "get-vectors", { text: concepts });
    return resp.vectors;
  });
}

function getEntities(
  clients: GraphRagClients,
  config: NormalizedGraphRagConfig,
  vectors: number[][],
  collection?: string,
): Effect.Effect<Term[], GraphRagEngineError> {
  return Effect.gen(function* () {
    const resp = yield* requestClient(
      clients.graphEmbeddings,
      "get-entities",
      {
        vectors,
        user: "default",
        collection: collection ?? "default",
        limit: config.entityLimit,
      },
    );
    return resp.entities;
  });
}

function followEdges(
  clients: GraphRagClients,
  config: NormalizedGraphRagConfig,
  entities: Term[],
  collection?: string,
): Effect.Effect<Triple[], GraphRagEngineError> {
  return Effect.gen(function* () {
    const visited = new Set<string>();
    const subgraph: Triple[] = [];
    let currentLevel = new Set<string>(
      entities.map((entity) => termToString(entity)),
    );

    for (let depth = 0; depth < config.maxPathLength; depth++) {
      if (currentLevel.size === 0 || subgraph.length >= config.maxSubgraphSize) {
        break;
      }

      const unvisited = [...currentLevel].filter((entity) => !visited.has(entity));
      if (unvisited.length === 0) break;

      const queries = unvisited.map((entityStr) => {
        const term = stringToTerm(entityStr);
        const request: TriplesQueryRequest = {
          s: term,
          limit: config.tripleLimit,
          ...(collection !== undefined ? { collection } : {}),
        };
        return requestClient(clients.triples, "follow-edges-query", request);
      });

      const results = yield* Effect.all(queries);
      const nextLevel = new Set<string>();

      for (const result of results) {
        for (const triple of result.triples) {
          subgraph.push(triple);

          if (depth < config.maxPathLength - 1) {
            const objStr = termToString(triple.o);
            if (!visited.has(objStr)) {
              nextLevel.add(objStr);
            }
          }

          if (subgraph.length >= config.maxSubgraphSize) {
            return subgraph;
          }
        }
      }

      for (const entity of currentLevel) {
        visited.add(entity);
      }
      currentLevel = nextLevel;
    }

    return subgraph.slice(0, config.maxSubgraphSize);
  });
}

function scoreEdges(
  clients: GraphRagClients,
  config: NormalizedGraphRagConfig,
  query: string,
  triples: Triple[],
): Effect.Effect<Triple[], GraphRagEngineError> {
  return Effect.gen(function* () {
    if (triples.length === 0) return [];

    if (triples.length <= 500) {
      yield* Effect.log(`[GraphRag] Skipping edge scoring - ${triples.length} triples fits in context directly`);
      return triples;
    }

    const edgeDescriptions = triples.map((triple, index) => ({
      id: String(index),
      s: termToString(triple.s),
      p: termToString(triple.p),
      o: termToString(triple.o),
    }));

    const toScore = edgeDescriptions.slice(0, config.edgeScoreLimit);
    const knowledgeJson = yield* S.encodeUnknownEffect(S.UnknownFromJsonString)(toScore).pipe(
      Effect.mapError((cause) => graphRagError("edge-score-encode", cause)),
    );

    const promptResp = yield* requestClient(
      clients.prompt,
      "edge-score-prompt",
      {
        name: "kg-edge-scoring",
        variables: {
          query,
          knowledge: knowledgeJson,
        },
      },
    );

    const llmResp = yield* requestClient(
      clients.llm,
      "edge-score-llm",
      {
        system: promptResp.system,
        prompt: promptResp.prompt,
      },
    );

    yield* Effect.log(`[GraphRag] Edge scoring LLM response (first 500 chars): ${llmResp.response.slice(0, 500)}`);

    const scored = parseScoredEdges(llmResp.response);
    scored.sort((a, b) => b.score - a.score);
    const topN = scored.slice(0, config.edgeLimit);

    const result: Triple[] = [];
    for (const entry of topN) {
      const idx = Number.parseInt(entry.id, 10);
      if (!Number.isNaN(idx) && idx >= 0 && idx < triples.length) {
        result.push(triples[idx]);
      }
    }

    yield* Effect.log(`[GraphRag] Edge scoring: LLM returned ${scored.length} scores, keeping top ${topN.length}, mapped ${result.length} triples`);

    if (result.length === 0) {
      return triples.slice(0, config.edgeLimit);
    }

    return result;
  });
}

function synthesize(
  clients: GraphRagClients,
  query: string,
  edges: Triple[],
  chunkCallback?: ChunkCallback,
): Effect.Effect<string, GraphRagEngineError> {
  return Effect.gen(function* () {
    const context = edges
      .map((triple) => `${termToString(triple.s)} -> ${termToString(triple.p)} -> ${termToString(triple.o)}`)
      .join("\n");

    const promptResp = yield* requestClient(
      clients.prompt,
      "synthesize-prompt",
      {
        name: "graph-rag-synthesize",
        variables: { query, context },
      },
    );

    if (chunkCallback !== undefined) {
      let fullText = "";
      yield* requestClient(
        clients.llm,
        "synthesize-stream",
        {
          system: promptResp.system,
          prompt: promptResp.prompt,
          streaming: true,
        },
        {
          recipient: (resp) => {
            if (resp.response.length === 0) {
              return Effect.succeed(resp.endOfStream === true);
            }
            fullText += resp.response;
            return Effect.tryPromise({
              try: () => chunkCallback(resp.response, resp.endOfStream === true).then(() => resp.endOfStream === true),
              catch: (cause) => graphRagError("synthesize-stream-callback", cause),
            });
          },
        },
      );
      return fullText;
    }

    const resp = yield* requestClient(
      clients.llm,
      "synthesize-llm",
      {
        system: promptResp.system,
        prompt: promptResp.prompt,
      },
    );

    return resp.response;
  });
}

const ScoredEdge = S.Struct({
  id: S.String,
  score: S.Number,
});
const ScoredEdgesFromJson = S.Array(ScoredEdge).pipe(S.fromJsonString);
const ScoredEdgeFromJson = ScoredEdge.pipe(S.fromJsonString);
const decodeScoredEdges = S.decodeUnknownOption(ScoredEdgesFromJson);
const decodeScoredEdge = S.decodeUnknownOption(ScoredEdgeFromJson);

function parseScoredEdges(responseText: string): Array<typeof ScoredEdge.Type> {
  const parsedArray = decodeScoredEdges(responseText);
  if (O.isSome(parsedArray)) {
    return Array.from(parsedArray.value);
  }

  const scored: Array<typeof ScoredEdge.Type> = [];
  for (const line of responseText.split("\n")) {
    const trimmed = line.trim();
    if (trimmed.length === 0) continue;
    const parsedLine = decodeScoredEdge(trimmed);
    if (O.isSome(parsedLine)) {
      scored.push(parsedLine.value);
    }
  }
  return scored;
}

export function termToString(term: Term): string {
  switch (term.type) {
    case "IRI":
      return term.iri;
    case "LITERAL":
      return term.value;
    case "BLANK":
      return `_:${term.id}`;
    case "TRIPLE":
      return `(${termToString(term.triple.s)} ${termToString(term.triple.p)} ${termToString(term.triple.o)})`;
  }
}

export function stringToTerm(value: string): Term {
  if (value.startsWith("http://") || value.startsWith("https://")) {
    return { type: "IRI", iri: value };
  }
  if (value.startsWith("_:")) {
    return { type: "BLANK", id: value.slice(2) };
  }
  return { type: "LITERAL", value };
}
