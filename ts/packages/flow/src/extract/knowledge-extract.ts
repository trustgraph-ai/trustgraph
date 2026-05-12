/**
 * Knowledge extraction service — extracts relationships and definitions from text chunks.
 *
 * A FlowProcessor that:
 * 1. Consumes Chunk messages
 * 2. Uses prompt service + LLM to extract relationships and definitions
 * 3. Converts extractions into RDF triples and entity contexts
 * 4. Emits Triples and EntityContexts messages
 *
 * Python reference: trustgraph-flow/trustgraph/extract/knowledge/service.py
 */

import {
  FlowProcessor,
  ConsumerSpec,
  ProducerSpec,
  RequestResponseSpec,
  type ProcessorConfig,
  type FlowContext,
  type Chunk,
  type Triples,
  type EntityContexts,
  type EntityContext,
  type PromptRequest,
  type PromptResponse,
  type TextCompletionRequest,
  type TextCompletionResponse,
  type Triple,
  type Term,
} from "@trustgraph/base";
import { makeProcessorProgram } from "@trustgraph/base";

// Well-known RDF/SKOS IRIs
const RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label";
const SKOS_DEFINITION = "http://www.w3.org/2004/02/skos/core#definition";

interface ExtractedRelationship {
  subject: string;
  predicate: string;
  object: string;
}

interface ExtractedDefinition {
  entity: string;
  definition: string;
}

export class KnowledgeExtractService extends FlowProcessor {
  constructor(config: ProcessorConfig) {
    super(config);

    this.registerSpecification(
      ConsumerSpec.fromPromise<Chunk>("extract-input", this.onMessage.bind(this)),
    );
    this.registerSpecification(new ProducerSpec<Triples>("extract-triples"));
    this.registerSpecification(new ProducerSpec<EntityContexts>("extract-entity-contexts"));

    this.registerSpecification(
      new RequestResponseSpec<PromptRequest, PromptResponse>(
        "prompt-client",
        "prompt-request",
        "prompt-response",
      ),
    );
    this.registerSpecification(
      new RequestResponseSpec<TextCompletionRequest, TextCompletionResponse>(
        "llm-client",
        "text-completion-request",
        "text-completion-response",
      ),
    );

    console.log("[KnowledgeExtract] Service initialized");
  }

  private async onMessage(
    msg: Chunk,
    properties: Record<string, string>,
    flowCtx: FlowContext,
  ): Promise<void> {
    const requestId = properties.id;
    if (requestId === undefined || requestId.length === 0) return;

    const text = msg.chunk;
    if (text.trim().length === 0) return;

    const promptClient = flowCtx.flow.requestor<PromptRequest, PromptResponse>("prompt-client");
    const llmClient = flowCtx.flow.requestor<TextCompletionRequest, TextCompletionResponse>("llm-client");
    const triplesProducer = flowCtx.flow.producer<Triples>("extract-triples");
    const entityContextsProducer = flowCtx.flow.producer<EntityContexts>("extract-entity-contexts");

    const allTriples: Triple[] = [];
    const allEntityContexts: EntityContext[] = [];

    // --- Extract relationships ---
    try {
      const relPrompt = await promptClient.request(
        { name: "extract-relationships", variables: { text } },
        { timeoutMs: 10_000 },
      );

      if (relPrompt.error === undefined) {
        let relationships: ExtractedRelationship[] | null = null;
        for (let attempt = 0; attempt < 3; attempt++) {
          const relCompletion = await llmClient.request(
            { system: relPrompt.system, prompt: relPrompt.prompt },
            { timeoutMs: 120_000 },
          );

          if (
            relCompletion.error === undefined &&
            relCompletion.response.length > 0
          ) {
            relationships = parseJsonResponse<ExtractedRelationship[]>(relCompletion.response);
            if (relationships !== null) break;
            console.warn(`[KnowledgeExtract] Relationship parse failed, attempt ${attempt + 1}/3`);
          } else {
            break; // LLM error, don't retry
          }
        }

        if (relationships !== null) {
          for (const rel of relationships) {
            if (
              rel.subject.length === 0 ||
              rel.predicate.length === 0 ||
              rel.object.length === 0
            ) {
              continue;
            }

            const subjectIri = toEntityIri(rel.subject);
            const predicateIri = toEntityIri(rel.predicate);
            const objectIri = toEntityIri(rel.object);

            // Main relationship triple
            allTriples.push({ s: subjectIri, p: predicateIri, o: objectIri });

            // rdfs:label triples for each entity
            allTriples.push({
              s: subjectIri,
              p: iriTerm(RDFS_LABEL),
              o: literalTerm(rel.subject),
            });
            allTriples.push({
              s: predicateIri,
              p: iriTerm(RDFS_LABEL),
              o: literalTerm(rel.predicate),
            });
            allTriples.push({
              s: objectIri,
              p: iriTerm(RDFS_LABEL),
              o: literalTerm(rel.object),
            });

            // Entity contexts for subject and object
            allEntityContexts.push({
              entity: subjectIri,
              context: text,
              chunkId: msg.documentId,
            });
            allEntityContexts.push({
              entity: objectIri,
              context: text,
              chunkId: msg.documentId,
            });
          }

          console.log(`[KnowledgeExtract] Extracted ${relationships.length} relationships`);
        }
      }
    } catch (err) {
      console.error("[KnowledgeExtract] Relationship extraction failed:", err);
    }

    // --- Extract definitions ---
    try {
      const defPrompt = await promptClient.request(
        { name: "extract-definitions", variables: { text } },
        { timeoutMs: 10_000 },
      );

      if (defPrompt.error === undefined) {
        let definitions: ExtractedDefinition[] | null = null;
        for (let attempt = 0; attempt < 3; attempt++) {
          const defCompletion = await llmClient.request(
            { system: defPrompt.system, prompt: defPrompt.prompt },
            { timeoutMs: 120_000 },
          );

          if (
            defCompletion.error === undefined &&
            defCompletion.response.length > 0
          ) {
            definitions = parseJsonResponse<ExtractedDefinition[]>(defCompletion.response);
            if (definitions !== null) break;
            console.warn(`[KnowledgeExtract] Definition parse failed, attempt ${attempt + 1}/3`);
          } else {
            break; // LLM error, don't retry
          }
        }

        if (definitions !== null) {
          for (const def of definitions) {
            if (def.entity.length === 0 || def.definition.length === 0) continue;

            const entityIri = toEntityIri(def.entity);

            // Definition triple
            allTriples.push({
              s: entityIri,
              p: iriTerm(SKOS_DEFINITION),
              o: literalTerm(def.definition),
            });

            // Label triple
            allTriples.push({
              s: entityIri,
              p: iriTerm(RDFS_LABEL),
              o: literalTerm(def.entity),
            });

            // Entity context
            allEntityContexts.push({
              entity: entityIri,
              context: text,
              chunkId: msg.documentId,
            });
          }

          console.log(`[KnowledgeExtract] Extracted ${definitions.length} definitions`);
        }
      }
    } catch (err) {
      console.error("[KnowledgeExtract] Definition extraction failed:", err);
    }

    // --- Emit results ---
    if (allTriples.length > 0) {
      await triplesProducer.send(requestId, {
        metadata: msg.metadata,
        triples: allTriples,
      });
    }

    if (allEntityContexts.length > 0) {
      await entityContextsProducer.send(requestId, {
        metadata: msg.metadata,
        entities: allEntityContexts,
      });
    }
  }
}

// ---------- Helpers ----------

function toEntityIri(name: string): Term {
  const slug = encodeURIComponent(name.toLowerCase().replace(/\s+/g, "-"));
  return {
    type: "IRI",
    iri: `http://trustgraph.ai/e/${slug}`,
  };
}

function iriTerm(iri: string): Term {
  return { type: "IRI", iri };
}

function literalTerm(value: string): Term {
  return { type: "LITERAL", value };
}

/**
 * Parse JSON from LLM output, handling markdown code fences and malformed output.
 * Uses progressive fallback: direct parse, array extraction, truncated array repair, single object wrap.
 */
export function parseJsonResponse<T>(raw: string): T | null {
  // Attempt 1: direct parse after stripping fences
  let cleaned = raw.trim();
  const fenceMatch = cleaned.match(/^```(?:json)?\s*\n?([\s\S]*?)\n?```$/);
  if (fenceMatch !== null) {
    cleaned = (fenceMatch[1] ?? "").trim();
  }

  try {
    return JSON.parse(cleaned) as T;
  } catch { /* fall through */ }

  // Attempt 2: extract first JSON array from the text
  const arrayMatch = cleaned.match(/\[[\s\S]*\]/);
  if (arrayMatch !== null) {
    try {
      return JSON.parse(arrayMatch[0]) as T;
    } catch { /* fall through */ }

    // Attempt 3: try to fix truncated array by closing it after the last complete object
    const partial = arrayMatch[0];
    const lastBrace = partial.lastIndexOf('}');
    if (lastBrace > 0) {
      const truncated = partial.slice(0, lastBrace + 1) + ']';
      try {
        return JSON.parse(truncated) as T;
      } catch { /* fall through */ }
    }
  }

  // Attempt 4: extract first JSON object, wrap in array
  const objMatch = cleaned.match(/\{[\s\S]*?\}/);
  if (objMatch !== null) {
    try {
      const obj = JSON.parse(objMatch[0]);
      return [obj] as unknown as T;
    } catch { /* fall through */ }
  }

  console.warn("[KnowledgeExtract] Failed to parse JSON from LLM response:", raw.slice(0, 300));
  return null;
}

export const program = makeProcessorProgram({
  id: "knowledge-extract",
  make: (config) => new KnowledgeExtractService(config),
});

export async function run(): Promise<void> {
  await KnowledgeExtractService.launch("knowledge-extract");
}
