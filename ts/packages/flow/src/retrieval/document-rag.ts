/**
 * Document RAG retrieval pipeline.
 *
 * Simpler than Graph RAG — embeds the query, finds similar document chunks,
 * and synthesizes an answer from the chunk content.
 *
 * Python reference: trustgraph-flow/trustgraph/retrieval/document_rag/
 */

import type {
  RequestResponse,
  TextCompletionRequest,
  TextCompletionResponse,
  EmbeddingsRequest,
  EmbeddingsResponse,
  PromptRequest,
  PromptResponse,
} from "@trustgraph/base";

export interface DocumentRagClients {
  llm: RequestResponse<TextCompletionRequest, TextCompletionResponse>;
  embeddings: RequestResponse<EmbeddingsRequest, EmbeddingsResponse>;
  docEmbeddings: RequestResponse<unknown, unknown>; // Doc embedding query
  prompt: RequestResponse<PromptRequest, PromptResponse>;
}

export type ChunkCallback = (text: string, endOfStream: boolean) => Promise<void>;

export class DocumentRag {
  constructor(private readonly clients: DocumentRagClients) {}

  async query(
    queryText: string,
    options?: {
      collection?: string;
      streaming?: boolean;
      chunkCallback?: ChunkCallback;
    },
  ): Promise<string> {
    // Step 1: Embed the query
    const embResp = await this.clients.embeddings.request({ text: [queryText] });
    const vectors = (embResp as EmbeddingsResponse).vectors;

    // Step 2: Find similar document chunks
    const docResp = await this.clients.docEmbeddings.request({ vectors, limit: 10 });
    const chunks = docResp as { chunks: Array<{ content: string; document: string }> };

    // Step 3: Build context from chunks
    const context = (chunks.chunks ?? [])
      .map((c) => c.content)
      .join("\n\n---\n\n");

    // Step 4: Synthesize answer
    const promptResp = await this.clients.prompt.request({
      name: "document-rag-synthesize",
      variables: { query: queryText, context },
    });

    const resp = await this.clients.llm.request({
      system: (promptResp as PromptResponse).system,
      prompt: (promptResp as PromptResponse).prompt,
    });

    return (resp as TextCompletionResponse).response;
  }
}
