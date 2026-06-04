/**
 * PDF decoder service — extracts text from PDF documents page by page.
 *
 * A FlowProcessor that:
 * 1. Consumes Document messages (documentId + pipeline metadata)
 * 2. Fetches document content from librarian via request/response
 * 3. Validates it is a PDF (checks MIME type from librarian metadata)
 * 4. Extracts text per page using pdfjs-dist
 * 5. Saves each page as a child document in librarian
 * 6. Emits TextDocument per page (to chunking pipeline)
 * 7. Emits Triples per page (provenance)
 *
 * Python reference: trustgraph-flow/trustgraph/decoding/pdf/decoder.py
 */

import { getDocument } from "pdfjs-dist/legacy/build/pdf.mjs";
import type { TextItem } from "pdfjs-dist/types/src/display/api.js";
import {
  makeFlowProcessor,
  makeConsumerSpec,
  makeProducerSpec,
  makeRequestResponseSpec,
  type ProcessorConfig,
  type FlowProcessorRuntime,
  type FlowContext,
  type FlowResourceNotFoundError,
  type Document,
  type TextDocument,
  type Triples,
  type Triple,
  type Term,
  type LibrarianRequest,
  type LibrarianResponse,
  type MessagingDeliveryError,
  type MessagingLifecycleError,
  type MessagingTimeoutError,
  type Spec,
  errorMessage,
} from "@trustgraph/base";
import { NodeRuntime } from "@effect/platform-node";
import { makeFlowProcessorProgram } from "@trustgraph/base";
import { Clock, Effect, Layer, ManagedRuntime } from "effect";
import * as S from "effect/Schema";

export class PdfDecoderError extends S.TaggedErrorClass<PdfDecoderError>()(
  "PdfDecoderError",
  {
    message: S.String,
    operation: S.String,
    documentId: S.String,
    cause: S.DefectWithStack,
  },
) {}

type PdfDecoderHandlerError =
  | FlowResourceNotFoundError
  | MessagingDeliveryError
  | MessagingLifecycleError
  | MessagingTimeoutError
  | PdfDecoderError;

type PdfDocument = Awaited<ReturnType<typeof getDocument>["promise"]>;

const pdfDecoderError = (
  operation: string,
  documentId: string,
  cause: unknown,
) =>
  PdfDecoderError.make({
    operation,
    documentId,
    message: errorMessage(cause),
    cause,
  });

const loadPdf = (documentId: string, pdfBuffer: Buffer) =>
  Effect.tryPromise({
    try: () => getDocument({ data: new Uint8Array(pdfBuffer) }).promise,
    catch: (cause) => pdfDecoderError("load-pdf", documentId, cause),
  });

const loadPageText = Effect.fn("loadPageText")(function*(
  documentId: string,
  pageNumber: number,
  pdf: PdfDocument,
) {
    const page = yield* Effect.tryPromise({
      try: () => pdf.getPage(pageNumber),
      catch: (cause) => pdfDecoderError("load-page", documentId, cause),
    });
    const textContent = yield* Effect.tryPromise({
      try: () => page.getTextContent(),
      catch: (cause) => pdfDecoderError("load-page-text", documentId, cause),
    });
    return textContent.items
      .filter((item): item is TextItem => "str" in item)
      .map((item) => item.str)
      .join(" ");
});

const DecodeOutputProducer = makeProducerSpec<TextDocument>("decode-output");
const DecodeTriplesProducer = makeProducerSpec<Triples>("decode-triples");
const LibrarianClient = makeRequestResponseSpec<LibrarianRequest, LibrarianResponse>(
  "librarian-client",
  "librarian-request",
  "librarian-response",
);

const onPdfDecodeMessage = Effect.fn("PdfDecoderService.onMessage")(function* (
  msg: Document,
  properties: Record<string, string>,
  flowCtx: FlowContext,
): Effect.fn.Return<void, PdfDecoderHandlerError> {
  const requestId = properties.id;
  if (requestId === undefined || requestId.length === 0) return;

  const { documentId } = msg;
  const user = msg.metadata.user;

  const librarian = yield* flowCtx.flow.requestorEffect(LibrarianClient);

  const metadataResp = yield* librarian.request({
    operation: "get-document-metadata",
    documentId,
    user,
  });

  if (metadataResp.error !== undefined) {
    yield* Effect.logError(`[PdfDecoder] Failed to get metadata for ${documentId}`, {
      error: metadataResp.error.message,
    });
    return;
  }

  const kind = metadataResp.documentMetadata?.kind;
  if (kind !== "application/pdf") {
    yield* Effect.log(`[PdfDecoder] Skipping document ${documentId}: kind=${kind} (not PDF)`);
    return;
  }

  const contentResp = yield* librarian.request({
    operation: "get-document-content",
    documentId,
    user,
  });

  if (
    contentResp.error !== undefined ||
    contentResp.content === undefined ||
    contentResp.content.length === 0
  ) {
    yield* Effect.logError(`[PdfDecoder] Failed to get content for ${documentId}`, {
      error: contentResp.error?.message ?? "no content",
    });
    return;
  }

  const pdfBuffer = Buffer.from(contentResp.content, "base64");
  const pdf = yield* loadPdf(documentId, pdfBuffer);

  yield* Effect.log(`[PdfDecoder] Document ${documentId}: ${pdf.numPages} pages`);

  const outputProducer = yield* flowCtx.flow.producerEffect(DecodeOutputProducer);
  const triplesProducer = yield* flowCtx.flow.producerEffect(DecodeTriplesProducer);

  for (let i = 1; i <= pdf.numPages; i++) {
    const pageText = yield* loadPageText(documentId, i, pdf);

    if (pageText.trim().length === 0) {
      yield* Effect.log(`[PdfDecoder] Skipping empty page ${i} of document ${documentId}`);
      continue;
    }

    const timestamp = yield* Clock.currentTimeMillis;
    const childResp = yield* librarian.request({
      operation: "add-child-document",
      documentMetadata: {
        id: "",
        user,
        kind: "text/plain",
        title: `Page ${i}`,
        parentId: documentId,
        documentType: "page",
        time: timestamp,
        comments: "",
        tags: [],
      },
      content: Buffer.from(pageText).toString("base64"),
    });

    if (childResp.error !== undefined) {
      yield* Effect.logError(`[PdfDecoder] Failed to save page ${i} of ${documentId}`, {
        error: childResp.error.message,
      });
      continue;
    }

    const childDocId = childResp.documentMetadata?.id ?? "";

    yield* outputProducer.send(requestId, {
      metadata: msg.metadata,
      text: pageText,
      documentId: childDocId,
    });

    const triples: Triple[] = [
      {
        s: iriTerm(`urn:tg:page:${childDocId}`),
        p: iriTerm("http://www.w3.org/ns/prov#wasDerivedFrom"),
        o: iriTerm(`urn:tg:doc:${documentId}`),
      },
      {
        s: iriTerm(`urn:tg:page:${childDocId}`),
        p: iriTerm("http://www.w3.org/2000/01/rdf-schema#label"),
        o: literalTerm(`Page ${i}`),
      },
    ];

    yield* triplesProducer.send(requestId, {
      metadata: msg.metadata,
      triples,
    });
  }

  yield* Effect.log(`[PdfDecoder] Finished processing document ${documentId}`);
});

export const makePdfDecoderSpecs = (): ReadonlyArray<Spec> => [
  makeConsumerSpec<Document, PdfDecoderHandlerError>("decode-input", onPdfDecodeMessage),
  DecodeOutputProducer,
  DecodeTriplesProducer,
  LibrarianClient,
];

export type PdfDecoderService = FlowProcessorRuntime;

export function makePdfDecoderService(config: ProcessorConfig): PdfDecoderService {
  const service = makeFlowProcessor(config, {
    specifications: makePdfDecoderSpecs(),
  });
  Effect.runSync(Effect.log("[PdfDecoder] Service initialized"));
  return service;
}

export const PdfDecoderService = makePdfDecoderService;

function iriTerm(iri: string): Term {
  return { type: "IRI", iri };
}

function literalTerm(value: string): Term {
  return { type: "LITERAL", value };
}

export const program = makeFlowProcessorProgram({
  id: "pdf-decoder",
  specs: () => makePdfDecoderSpecs(),
});

const pdfDecoderRuntime = ManagedRuntime.make(Layer.empty);

export function run(): Promise<void> {
  return pdfDecoderRuntime.runPromise(program);
}

export function runMain(): void {
  NodeRuntime.runMain(program);
}
