/**
 * Document RAG service — FlowProcessor wrapper around the DocumentRag class.
 *
 * Consumes DocumentRagRequest messages, runs the document retrieval pipeline
 * (embed query → find similar chunks → synthesize answer), emits DocumentRagResponse.
 *
 * Each request gets its own DocumentRag instance for security isolation.
 *
 * Python reference: trustgraph-flow/trustgraph/retrieval/document_rag/
 */

import {
  FlowProcessor,
  ConsumerSpec,
  ProducerSpec,
  RequestResponseSpec,
  type ProcessorConfig,
  type FlowContext,
  type DocumentRagRequest,
  type DocumentRagResponse,
  type TextCompletionRequest,
  type TextCompletionResponse,
  type EmbeddingsRequest,
  type EmbeddingsResponse,
  type DocumentEmbeddingsRequest,
  type DocumentEmbeddingsResponse,
  type PromptRequest,
  type PromptResponse,
} from "@trustgraph/base";
import { DocumentRag } from "./document-rag.js";

export class DocumentRagService extends FlowProcessor {
  constructor(config: ProcessorConfig) {
    super(config);

    // Consumer: document RAG requests
    this.registerSpecification(
      new ConsumerSpec<DocumentRagRequest>("document-rag-request", this.onRequest.bind(this)),
    );

    // Producer: document RAG responses
    this.registerSpecification(new ProducerSpec<DocumentRagResponse>("document-rag-response"));

    // Request-response clients
    this.registerSpecification(
      new RequestResponseSpec<TextCompletionRequest, TextCompletionResponse>(
        "llm",
        "text-completion-request",
        "text-completion-response",
      ),
    );
    this.registerSpecification(
      new RequestResponseSpec<EmbeddingsRequest, EmbeddingsResponse>(
        "embeddings",
        "embeddings-request",
        "embeddings-response",
      ),
    );
    this.registerSpecification(
      new RequestResponseSpec<DocumentEmbeddingsRequest, DocumentEmbeddingsResponse>(
        "doc-embeddings",
        "document-embeddings-request",
        "document-embeddings-response",
      ),
    );
    this.registerSpecification(
      new RequestResponseSpec<PromptRequest, PromptResponse>(
        "prompt",
        "prompt-request",
        "prompt-response",
      ),
    );

    console.log("[DocumentRag] Service initialized");
  }

  private async onRequest(
    msg: DocumentRagRequest,
    properties: Record<string, string>,
    flowCtx: FlowContext,
  ): Promise<void> {
    const requestId = properties.id;
    if (!requestId) return;

    const producer = flowCtx.flow.producer<DocumentRagResponse>("document-rag-response");

    try {
      const documentRag = new DocumentRag({
        llm: flowCtx.flow.requestor<TextCompletionRequest, TextCompletionResponse>("llm"),
        embeddings: flowCtx.flow.requestor<EmbeddingsRequest, EmbeddingsResponse>("embeddings"),
        docEmbeddings: flowCtx.flow.requestor<DocumentEmbeddingsRequest, DocumentEmbeddingsResponse>("doc-embeddings"),
        prompt: flowCtx.flow.requestor<PromptRequest, PromptResponse>("prompt"),
      });

      const response = await documentRag.query(msg.query, {
        collection: msg.collection,
      });

      await producer.send(requestId, { response });
    } catch (err) {
      console.error("[DocumentRag] Query failed:", err);
      await producer.send(requestId, {
        response: "",
        error: { type: "rag-error", message: String(err) },
      });
    }
  }
}

export async function run(): Promise<void> {
  await DocumentRagService.launch("document-rag");
}
