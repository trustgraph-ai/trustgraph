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
  FlowProcessor,
  ConsumerSpec,
  ProducerSpec,
  RequestResponseSpec,
  type ProcessorConfig,
  type FlowContext,
  type Document,
  type TextDocument,
  type Triples,
  type Triple,
  type Term,
  type LibrarianRequest,
  type LibrarianResponse,
} from "@trustgraph/base";
import { makeProcessorProgram } from "@trustgraph/base";

export class PdfDecoderService extends FlowProcessor {
  constructor(config: ProcessorConfig) {
    super(config);

    this.registerSpecification(
      ConsumerSpec.fromPromise<Document>("decode-input", this.onMessage.bind(this)),
    );
    this.registerSpecification(new ProducerSpec<TextDocument>("decode-output"));
    this.registerSpecification(new ProducerSpec<Triples>("decode-triples"));
    this.registerSpecification(
      new RequestResponseSpec<LibrarianRequest, LibrarianResponse>(
        "librarian-client",
        "librarian-request",
        "librarian-response",
      ),
    );

    console.log("[PdfDecoder] Service initialized");
  }

  private async onMessage(
    msg: Document,
    properties: Record<string, string>,
    flowCtx: FlowContext,
  ): Promise<void> {
    const requestId = properties.id;
    if (requestId === undefined || requestId.length === 0) return;

    const { documentId } = msg;
    const user = msg.metadata.user;

    const librarian = flowCtx.flow.requestor<LibrarianRequest, LibrarianResponse>(
      "librarian-client",
    );

    // 1. Fetch document metadata to check MIME type
    const metadataResp = await librarian.request({
      operation: "get-document-metadata",
      documentId,
      user,
    });

    if (metadataResp.error !== undefined) {
      console.error(
        `[PdfDecoder] Failed to get metadata for ${documentId}:`,
        metadataResp.error.message,
      );
      return;
    }

    const kind = metadataResp.documentMetadata?.kind;
    if (kind !== "application/pdf") {
      console.log(
        `[PdfDecoder] Skipping document ${documentId}: kind=${kind} (not PDF)`,
      );
      return;
    }

    // 2. Fetch document content
    const contentResp = await librarian.request({
      operation: "get-document-content",
      documentId,
      user,
    });

    if (
      contentResp.error !== undefined ||
      contentResp.content === undefined ||
      contentResp.content.length === 0
    ) {
      console.error(
        `[PdfDecoder] Failed to get content for ${documentId}:`,
        contentResp.error?.message ?? "no content",
      );
      return;
    }

    // 3. Decode base64 content and extract text per page
    const pdfBuffer = Buffer.from(contentResp.content, "base64");
    const pdf = await getDocument({ data: new Uint8Array(pdfBuffer) }).promise;

    console.log(
      `[PdfDecoder] Document ${documentId}: ${pdf.numPages} pages`,
    );

    const outputProducer = flowCtx.flow.producer<TextDocument>("decode-output");
    const triplesProducer = flowCtx.flow.producer<Triples>("decode-triples");

    for (let i = 1; i <= pdf.numPages; i++) {
      const page = await pdf.getPage(i);
      const textContent = await page.getTextContent();
      const pageText = textContent.items
        .filter((item): item is TextItem => "str" in item)
        .map((item) => item.str)
        .join(" ");

      if (pageText.trim().length === 0) {
        console.log(
          `[PdfDecoder] Skipping empty page ${i} of document ${documentId}`,
        );
        continue;
      }

      // 4. Save as child document in librarian
      const childResp = await librarian.request({
        operation: "add-child-document",
        documentMetadata: {
          id: "",
          user,
          kind: "text/plain",
          title: `Page ${i}`,
          parentId: documentId,
          documentType: "page",
          time: Date.now(),
          comments: "",
          tags: [],
        },
        content: Buffer.from(pageText).toString("base64"),
      });

      if (childResp.error !== undefined) {
        console.error(
          `[PdfDecoder] Failed to save page ${i} of ${documentId}:`,
          childResp.error.message,
        );
        continue;
      }

      const childDocId = childResp.documentMetadata?.id ?? "";

      // 5. Emit TextDocument for the chunking pipeline
      await outputProducer.send(requestId, {
        metadata: msg.metadata,
        text: pageText,
        documentId: childDocId,
      });

      // 6. Emit provenance triples
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

      await triplesProducer.send(requestId, {
        metadata: msg.metadata,
        triples,
      });
    }

    console.log(
      `[PdfDecoder] Finished processing document ${documentId}`,
    );
  }
}

function iriTerm(iri: string): Term {
  return { type: "IRI", iri };
}

function literalTerm(value: string): Term {
  return { type: "LITERAL", value };
}

export const program = makeProcessorProgram({
  id: "pdf-decoder",
  make: (config) => new PdfDecoderService(config),
});

export async function run(): Promise<void> {
  await PdfDecoderService.launch("pdf-decoder");
}
