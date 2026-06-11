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

import type {
  ProcessorConfig,
  FlowProcessorRuntime,
  FlowContext,
  Chunk,
  Triples,
  EntityContexts,
  EntityContext,
  PromptRequest,
  PromptResponse,
  TextCompletionRequest,
  TextCompletionResponse,
  Triple,
  Term,
  FlowResourceNotFoundError,
  MessagingDeliveryError,
  EffectRequestResponse,
  Spec,
} from "@trustgraph/base";
import {
  errorMessage,
  makeFlowProcessor,
  makeConsumerSpec,
  makeProducerSpec,
  makeRequestResponseSpec,
  makeFlowProcessorProgram,
} from "@trustgraph/base";
import { NodeRuntime } from "@effect/platform-node";
import { Effect } from "effect";
import * as O from "effect/Option";
import * as S from "effect/Schema";

// Well-known RDF/SKOS IRIs
const RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label";
const SKOS_DEFINITION = "http://www.w3.org/2004/02/skos/core#definition";

const ExtractedRelationship = S.Struct({
  subject: S.String,
  predicate: S.String,
  object: S.String,
});
type ExtractedRelationship = typeof ExtractedRelationship.Type;

const ExtractedRelationshipsFromJson = S.Array(ExtractedRelationship).pipe(S.fromJsonString);
const decodeExtractedRelationships = S.decodeUnknownOption(ExtractedRelationshipsFromJson);

const ExtractedDefinition = S.Struct({
  entity: S.String,
  definition: S.String,
});
type ExtractedDefinition = typeof ExtractedDefinition.Type;

const ExtractedDefinitionsFromJson = S.Array(ExtractedDefinition).pipe(S.fromJsonString);
const decodeExtractedDefinitions = S.decodeUnknownOption(ExtractedDefinitionsFromJson);

type KnowledgeExtractHandlerError =
  | FlowResourceNotFoundError
  | MessagingDeliveryError;

type PromptClient = EffectRequestResponse<PromptRequest, PromptResponse>;
type LlmClient = EffectRequestResponse<TextCompletionRequest, TextCompletionResponse>;

const ExtractTriplesProducer = makeProducerSpec<Triples>("extract-triples");
const ExtractEntityContextsProducer = makeProducerSpec<EntityContexts>("extract-entity-contexts");
const PromptClientSpec = makeRequestResponseSpec<PromptRequest, PromptResponse>(
  "prompt-client",
  "prompt-request",
  "prompt-response",
);
const LlmClientSpec = makeRequestResponseSpec<TextCompletionRequest, TextCompletionResponse>(
  "llm-client",
  "text-completion-request",
  "text-completion-response",
);

const requestPrompt = Effect.fn("KnowledgeExtract.requestPrompt")(function* (
  promptClient: PromptClient,
  name: string,
  text: string,
) {
  return yield* promptClient.request(
    { name, variables: { text } },
    { timeoutMs: 10_000 },
  );
});

const requestCompletion = Effect.fn("KnowledgeExtract.requestCompletion")(function* (
  llmClient: LlmClient,
  prompt: PromptResponse,
) {
  return yield* llmClient.request(
    { system: prompt.system, prompt: prompt.prompt },
    { timeoutMs: 120_000 },
  );
});

const extractRelationships = Effect.fn("KnowledgeExtract.extractRelationships")(function* (
  promptClient: PromptClient,
  llmClient: LlmClient,
  text: string,
) {
  const relPrompt = yield* requestPrompt(promptClient, "extract-relationships", text);
  if (relPrompt.error !== undefined) return null;

  for (let attempt = 0; attempt < 3; attempt++) {
    const relCompletion = yield* requestCompletion(llmClient, relPrompt);

    if (relCompletion.error !== undefined || relCompletion.response.length === 0) {
      break;
    }

    const relationships = parseRelationshipsResponse(relCompletion.response);
    if (relationships !== null) return relationships;

    yield* Effect.logWarning(
      `[KnowledgeExtract] Relationship parse failed, attempt ${attempt + 1}/3`,
    );
  }

  return null;
});

const extractDefinitions = Effect.fn("KnowledgeExtract.extractDefinitions")(function* (
  promptClient: PromptClient,
  llmClient: LlmClient,
  text: string,
) {
  const defPrompt = yield* requestPrompt(promptClient, "extract-definitions", text);
  if (defPrompt.error !== undefined) return null;

  for (let attempt = 0; attempt < 3; attempt++) {
    const defCompletion = yield* requestCompletion(llmClient, defPrompt);

    if (defCompletion.error !== undefined || defCompletion.response.length === 0) {
      break;
    }

    const definitions = parseDefinitionsResponse(defCompletion.response);
    if (definitions !== null) return definitions;

    yield* Effect.logWarning(
      `[KnowledgeExtract] Definition parse failed, attempt ${attempt + 1}/3`,
    );
  }

  return null;
});

const onKnowledgeExtractMessage = Effect.fn("KnowledgeExtractService.onMessage")(function* (
  msg: Chunk,
  properties: Record<string, string>,
  flowCtx: FlowContext,
): Effect.fn.Return<void, KnowledgeExtractHandlerError> {
  const requestId = properties.id;
  if (requestId === undefined || requestId.length === 0) return;

  const text = msg.chunk;
  if (text.trim().length === 0) return;

  const promptClient = yield* flowCtx.flow.requestorEffect(PromptClientSpec);
  const llmClient = yield* flowCtx.flow.requestorEffect(LlmClientSpec);
  const triplesProducer = yield* flowCtx.flow.producerEffect(ExtractTriplesProducer);
  const entityContextsProducer = yield* flowCtx.flow.producerEffect(ExtractEntityContextsProducer);

  const allTriples: Triple[] = [];
  const allEntityContexts: EntityContext[] = [];

  const relationships = yield* extractRelationships(promptClient, llmClient, text).pipe(
    Effect.catch((error: unknown) =>
      Effect.logError("[KnowledgeExtract] Relationship extraction failed", {
        error: errorMessage(error),
      }).pipe(Effect.as(null)),
    ),
  );

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

      allTriples.push({ s: subjectIri, p: predicateIri, o: objectIri });
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

    yield* Effect.log(`[KnowledgeExtract] Extracted ${relationships.length} relationships`);
  }

  const definitions = yield* extractDefinitions(promptClient, llmClient, text).pipe(
    Effect.catch((error: unknown) =>
      Effect.logError("[KnowledgeExtract] Definition extraction failed", {
        error: errorMessage(error),
      }).pipe(Effect.as(null)),
    ),
  );

  if (definitions !== null) {
    for (const def of definitions) {
      if (def.entity.length === 0 || def.definition.length === 0) continue;

      const entityIri = toEntityIri(def.entity);

      allTriples.push({
        s: entityIri,
        p: iriTerm(SKOS_DEFINITION),
        o: literalTerm(def.definition),
      });
      allTriples.push({
        s: entityIri,
        p: iriTerm(RDFS_LABEL),
        o: literalTerm(def.entity),
      });

      allEntityContexts.push({
        entity: entityIri,
        context: text,
        chunkId: msg.documentId,
      });
    }

    yield* Effect.log(`[KnowledgeExtract] Extracted ${definitions.length} definitions`);
  }

  if (allTriples.length > 0) {
    yield* triplesProducer.send(requestId, {
      metadata: msg.metadata,
      triples: allTriples,
    });
  }

  if (allEntityContexts.length > 0) {
    yield* entityContextsProducer.send(requestId, {
      metadata: msg.metadata,
      entities: allEntityContexts,
    });
  }
});

export const makeKnowledgeExtractSpecs = (): ReadonlyArray<Spec> => [
  makeConsumerSpec<Chunk, KnowledgeExtractHandlerError>(
    "extract-input",
    onKnowledgeExtractMessage,
  ),
  ExtractTriplesProducer,
  ExtractEntityContextsProducer,
  PromptClientSpec,
  LlmClientSpec,
];

export type KnowledgeExtractService = FlowProcessorRuntime;

export function makeKnowledgeExtractService(config: ProcessorConfig): KnowledgeExtractService {
  return makeFlowProcessor(config, {
    specifications: makeKnowledgeExtractSpecs(),
  });
}

export const KnowledgeExtractService = makeKnowledgeExtractService;

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
  const decodeJson = S.decodeUnknownOption(S.UnknownFromJsonString);
  for (const candidate of jsonCandidates(raw)) {
    const decoded = decodeJson(candidate);
    if (O.isSome(decoded)) return decoded.value as T;
  }

  return null;
}

function parseRelationshipsResponse(raw: string): ReadonlyArray<ExtractedRelationship> | null {
  for (const candidate of jsonCandidates(raw)) {
    const decoded = decodeExtractedRelationships(candidate);
    if (O.isSome(decoded)) return decoded.value;
  }
  return null;
}

function parseDefinitionsResponse(raw: string): ReadonlyArray<ExtractedDefinition> | null {
  for (const candidate of jsonCandidates(raw)) {
    const decoded = decodeExtractedDefinitions(candidate);
    if (O.isSome(decoded)) return decoded.value;
  }
  return null;
}

function jsonCandidates(raw: string): ReadonlyArray<string> {
  const candidates: string[] = [];
  let cleaned = raw.trim();
  const fenceMatch = cleaned.match(/^```(?:json)?\s*\n?([\s\S]*?)\n?```$/);
  if (fenceMatch !== null) {
    cleaned = (fenceMatch[1] ?? "").trim();
  }

  candidates.push(cleaned);

  const arrayMatch = cleaned.match(/\[[\s\S]*\]/);
  if (arrayMatch !== null) {
    candidates.push(arrayMatch[0]);

    const partial = arrayMatch[0];
    const lastBrace = partial.lastIndexOf("}");
    if (lastBrace > 0) {
      candidates.push(`${partial.slice(0, lastBrace + 1)}]`);
    }
  }

  const objMatch = cleaned.match(/\{[\s\S]*?\}/);
  if (objMatch !== null) {
    candidates.push(`[${objMatch[0]}]`);
  }

  return candidates;
}

export const program = makeFlowProcessorProgram({
  id: "knowledge-extract",
  specs: () => makeKnowledgeExtractSpecs(),
});

export function runMain(): void {
  NodeRuntime.runMain(program);
}
