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
    // BFS multi-hop traversal up to maxPathLength
    const visited = new Set<string>();
    const subgraph: Triple[] = [];

    // Current frontier: the set of entities to expand at this depth level
    let currentLevel = new Set<string>(
      entities.map((e) => termToString(e)),
    );

    for (let depth = 0; depth < this.config.maxPathLength; depth++) {
      if (currentLevel.size === 0 || subgraph.length >= this.config.maxSubgraphSize) {
        break;
      }

      // Filter out already-visited entities
      const unvisited = [...currentLevel].filter((e) => !visited.has(e));
      if (unvisited.length === 0) break;

      // Batch triple queries for all unvisited entities at this depth
      // Query each entity as subject to get outgoing edges
      const queries = unvisited.map((entityStr) => {
        const term = stringToTerm(entityStr);
        return this.clients.triples.request({
          s: term,
          limit: this.config.tripleLimit,
        });
      });

      const results = await Promise.all(queries);

      const nextLevel = new Set<string>();

      for (const result of results) {
        const triples = (result as TriplesQueryResponse).triples;
        for (const triple of triples) {
          subgraph.push(triple);

          // Collect objects as next-level entities for further expansion
          // (only if we have more depth levels remaining)
          if (depth < this.config.maxPathLength - 1) {
            const objStr = termToString(triple.o);
            if (!visited.has(objStr)) {
              nextLevel.add(objStr);
            }
          }

          if (subgraph.length >= this.config.maxSubgraphSize) {
            return subgraph;
          }
        }
      }

      // Mark current level as visited and move to next
      for (const e of currentLevel) {
        visited.add(e);
      }
      currentLevel = nextLevel;
    }

    return subgraph.slice(0, this.config.maxSubgraphSize);
  }

  private async scoreEdges(query: string, triples: Triple[]): Promise<Triple[]> {
    if (triples.length === 0) return [];

    // If the subgraph is small enough, skip LLM scoring entirely
    if (triples.length <= this.config.edgeLimit) {
      return triples;
    }

    // Build a numbered list of edges for the LLM to score
    const edgeDescriptions = triples.map((t, i) => ({
      id: String(i),
      s: termToString(t.s),
      p: termToString(t.p),
      o: termToString(t.o),
    }));

    // Limit how many edges we send for scoring to avoid overflowing context
    const toScore = edgeDescriptions.slice(0, this.config.edgeScoreLimit);

    const knowledgeJson = JSON.stringify(toScore, null, 2);

    // Ask the LLM to score each edge for relevance to the query
    const promptResp = await this.clients.prompt.request({
      name: "kg-edge-scoring",
      variables: {
        query,
        knowledge: knowledgeJson,
      },
    });

    const llmResp = await this.clients.llm.request({
      system: (promptResp as PromptResponse).system,
      prompt: (promptResp as PromptResponse).prompt,
    });

    const responseText = (llmResp as TextCompletionResponse).response;

    // Parse scores from LLM response
    // Expected format: JSON array of { id: string, score: number }
    // or newline-separated JSON objects
    const scored: Array<{ id: string; score: number }> = [];

    try {
      // Try parsing as a JSON array first
      const parsed = JSON.parse(responseText) as Array<{ id: string; score: number }>;
      if (Array.isArray(parsed)) {
        for (const item of parsed) {
          if (item && typeof item.id === "string" && typeof item.score === "number") {
            scored.push({ id: item.id, score: item.score });
          }
        }
      }
    } catch {
      // Fall back to parsing line-by-line JSON objects
      for (const line of responseText.split("\n")) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        try {
          const obj = JSON.parse(trimmed) as { id?: string; score?: number };
          if (obj && typeof obj.id === "string" && typeof obj.score === "number") {
            scored.push({ id: obj.id, score: obj.score });
          }
        } catch {
          // Skip unparseable lines
        }
      }
    }

    // Sort by score descending and keep top N
    scored.sort((a, b) => b.score - a.score);
    const topN = scored.slice(0, this.config.edgeLimit);
    const selectedIds = new Set(topN.map((e) => e.id));

    // Map back to triples
    const result: Triple[] = [];
    for (const entry of topN) {
      const idx = parseInt(entry.id, 10);
      if (!isNaN(idx) && idx >= 0 && idx < triples.length) {
        result.push(triples[idx]);
      }
    }

    // If scoring failed entirely, fall back to returning the first edgeLimit triples
    if (result.length === 0) {
      return triples.slice(0, this.config.edgeLimit);
    }

    return result;
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

function stringToTerm(value: string): Term {
  if (value.startsWith("http://") || value.startsWith("https://")) {
    return { type: "IRI", iri: value };
  }
  if (value.startsWith("_:")) {
    return { type: "BLANK", id: value.slice(2) };
  }
  return { type: "LITERAL", value };
}
