/**
 * Graph RAG retrieval pipeline.
 *
 * This is the core RAG pipeline that:
 * 1. Extracts concepts from the query
 * 2. Embeds concepts to find matching entities
 * 3. Traverses the knowledge graph from those entities
 * 4. Scores and filters edges
 * 5. Synthesizes an answer with the selected context
 *
 * Python reference: trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py
 */

import type {
  RequestResponse,
  TextCompletionRequest,
  TextCompletionResponse,
  EmbeddingsRequest,
  EmbeddingsResponse,
  GraphEmbeddingsRequest,
  GraphEmbeddingsResponse,
  TriplesQueryRequest,
  TriplesQueryResponse,
  PromptRequest,
  PromptResponse,
  Term,
  Triple,
} from "@trustgraph/base";

export interface GraphRagConfig {
  entityLimit?: number;
  tripleLimit?: number;
  maxSubgraphSize?: number;
  maxPathLength?: number;
  edgeScoreLimit?: number;
  edgeLimit?: number;
}

export interface GraphRagClients {
  llm: RequestResponse<TextCompletionRequest, TextCompletionResponse>;
  embeddings: RequestResponse<EmbeddingsRequest, EmbeddingsResponse>;
  graphEmbeddings: RequestResponse<GraphEmbeddingsRequest, GraphEmbeddingsResponse>;
  triples: RequestResponse<TriplesQueryRequest, TriplesQueryResponse>;
  prompt: RequestResponse<PromptRequest, PromptResponse>;
}

export type ChunkCallback = (text: string, endOfStream: boolean) => Promise<void>;

export class GraphRag {
  private config: Required<GraphRagConfig>;

  constructor(
    private readonly clients: GraphRagClients,
    config: GraphRagConfig = {},
  ) {
    this.config = {
      entityLimit: config.entityLimit ?? 50,
      tripleLimit: config.tripleLimit ?? 30,
      maxSubgraphSize: config.maxSubgraphSize ?? 1000,
      maxPathLength: config.maxPathLength ?? 2,
      edgeScoreLimit: config.edgeScoreLimit ?? 30,
      edgeLimit: config.edgeLimit ?? 25,
    };
  }

  async query(
    queryText: string,
    options?: {
      collection?: string;
      streaming?: boolean;
      chunkCallback?: ChunkCallback;
    },
  ): Promise<string> {
    // Step 1: Extract concepts from the query via prompt + LLM
    const concepts = await this.extractConcepts(queryText);

    // Step 2: Embed concepts concurrently
    const vectors = await this.getVectors(concepts);

    // Step 3: Find matching entities via graph embeddings
    const entities = await this.getEntities(vectors);

    // Step 4: Traverse the knowledge graph from entities
    const subgraph = await this.followEdges(entities);

    // Step 5: Score and filter edges via LLM
    const scoredEdges = await this.scoreEdges(queryText, subgraph);

    // Step 6: Synthesize answer
    const answer = await this.synthesize(queryText, scoredEdges, options?.chunkCallback);

    return answer;
  }

  private async extractConcepts(query: string): Promise<string[]> {
    const promptResp = await this.clients.prompt.request({
      name: "extract-concepts",
      variables: { query },
    });

    const llmResp = await this.clients.llm.request({
      system: (promptResp as PromptResponse).system,
      prompt: (promptResp as PromptResponse).prompt,
    });

    // Parse concepts from LLM response (newline-separated)
    return (llmResp as TextCompletionResponse).response
      .split("\n")
      .map((c) => c.trim())
      .filter(Boolean);
  }

  private async getVectors(concepts: string[]): Promise<number[][]> {
    const resp = await this.clients.embeddings.request({ text: concepts });
    return (resp as EmbeddingsResponse).vectors;
  }

  private async getEntities(vectors: number[][]): Promise<Term[]> {
    const resp = await this.clients.graphEmbeddings.request({
      vectors,
      limit: this.config.entityLimit,
    });
    return (resp as GraphEmbeddingsResponse).entities;
  }

  private async followEdges(entities: Term[]): Promise<Triple[]> {
    // Batch triple queries for all entities
    const allTriples: Triple[] = [];

    const queries = entities.map((entity) =>
      this.clients.triples.request({ s: entity, limit: this.config.tripleLimit }),
    );

    const results = await Promise.all(queries);
    for (const result of results) {
      allTriples.push(...(result as TriplesQueryResponse).triples);
    }

    // TODO: Multi-hop traversal up to maxPathLength
    return allTriples.slice(0, this.config.maxSubgraphSize);
  }

  private async scoreEdges(query: string, triples: Triple[]): Promise<Triple[]> {
    // TODO: LLM-based edge scoring and filtering
    // For now, return top N edges
    return triples.slice(0, this.config.edgeLimit);
  }

  private async synthesize(
    query: string,
    edges: Triple[],
    chunkCallback?: ChunkCallback,
  ): Promise<string> {
    // Format edges as context
    const context = edges
      .map((t) => `${termToString(t.s)} -> ${termToString(t.p)} -> ${termToString(t.o)}`)
      .join("\n");

    const promptResp = await this.clients.prompt.request({
      name: "graph-rag-synthesize",
      variables: { query, context },
    });

    if (chunkCallback) {
      // Streaming response
      let fullText = "";
      await this.clients.llm.request(
        {
          system: (promptResp as PromptResponse).system,
          prompt: (promptResp as PromptResponse).prompt,
          streaming: true,
        },
        {
          recipient: async (resp) => {
            const r = resp as TextCompletionResponse;
            if (r.response) {
              fullText += r.response;
              await chunkCallback(r.response, !!r.endOfStream);
            }
            return !!r.endOfStream;
          },
        },
      );
      return fullText;
    }

    const resp = await this.clients.llm.request({
      system: (promptResp as PromptResponse).system,
      prompt: (promptResp as PromptResponse).prompt,
    });

    return (resp as TextCompletionResponse).response;
  }
}

function termToString(term: Term): string {
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
