import type { DocumentMetadata, ProcessingMetadata, StreamingMetadata, Triple } from "@trustgraph/client";
import { Array as A, Match, Option, Order, Schema as S } from "effect";

type ConfigValues = Record<string, Record<string, unknown>>;

export interface WorkbenchQaApi {
  readonly makeRequest: <RequestType extends object, ResponseType>(
    service: string,
    request: RequestType,
    timeout?: number,
    retries?: number,
    flow?: string,
  ) => Promise<ResponseType>;
  readonly makeRequestMulti: <RequestType extends object, ResponseType>(
    service: string,
    request: RequestType,
    receiver: (resp: unknown) => boolean,
    timeout?: number,
    retries?: number,
    flow?: string,
  ) => Promise<ResponseType>;
}

const UnknownRecord = S.Record(S.String, S.Unknown);
const ConfigValuesRecord = S.Record(S.String, UnknownRecord);

const ClientTerm: S.Codec<Triple["s"], Triple["s"]> = S.suspend(() =>
  S.Union([
    S.Struct({ t: S.Literal("i"), i: S.String }),
    S.Struct({ t: S.Literal("b"), d: S.String }),
    S.Struct({
      t: S.Literal("l"),
      v: S.String,
      dt: S.optionalKey(S.String),
      ln: S.optionalKey(S.String),
    }),
    S.Struct({
      t: S.Literal("t"),
      tr: S.optionalKey(ClientTriple),
    }),
  ])
);

const ClientTriple: S.Codec<Triple, Triple> = S.suspend(() =>
  S.Struct({
    s: ClientTerm,
    p: ClientTerm,
    o: ClientTerm,
    g: S.optionalKey(S.String),
  })
);

const DocumentMetadataValue: S.Codec<DocumentMetadata, DocumentMetadata> = S.Struct({
  id: S.optionalKey(S.String),
  time: S.optionalKey(S.Finite),
  kind: S.optionalKey(S.String),
  title: S.optionalKey(S.String),
  comments: S.optionalKey(S.String),
  metadata: S.optionalKey(S.Array(ClientTriple).pipe(S.mutable)),
  user: S.optionalKey(S.String),
  tags: S.optionalKey(S.Array(S.String).pipe(S.mutable)),
  parentId: S.optionalKey(S.String),
  documentType: S.optionalKey(S.String),
  "parent-id": S.optionalKey(S.String),
  "document-type": S.optionalKey(S.String),
});

const ProcessingMetadataValue: S.Codec<ProcessingMetadata, ProcessingMetadata> = S.Struct({
  id: S.optionalKey(S.String),
  "document-id": S.optionalKey(S.String),
  documentId: S.optionalKey(S.String),
  time: S.optionalKey(S.Finite),
  flow: S.optionalKey(S.String),
  user: S.optionalKey(S.String),
  collection: S.optionalKey(S.String),
  tags: S.optionalKey(S.Array(S.String).pipe(S.mutable)),
});

export class MockWorkbenchFixture extends S.Class<MockWorkbenchFixture>("MockWorkbenchFixture")({
  settings: S.optionalKey(S.Struct({
    user: S.optionalKey(S.String),
    apiKey: S.optionalKey(S.String),
    gatewayUrl: S.optionalKey(S.String),
    collection: S.optionalKey(S.String),
    featureSwitches: S.optionalKey(S.Record(S.String, S.Boolean)),
  })),
  flows: S.optionalKey(S.Struct({
    activeIds: S.optionalKey(S.Array(S.String).pipe(S.mutable)),
    definitions: S.optionalKey(S.Record(S.String, UnknownRecord)),
    blueprints: S.optionalKey(S.Record(S.String, UnknownRecord)),
  })),
  config: S.optionalKey(S.Struct({
    prompt: S.optionalKey(UnknownRecord),
    valuesByType: S.optionalKey(ConfigValuesRecord),
  })),
  library: S.optionalKey(S.Struct({
    documents: S.optionalKey(S.Array(DocumentMetadataValue).pipe(S.mutable)),
    processing: S.optionalKey(S.Array(ProcessingMetadataValue).pipe(S.mutable)),
    metadataById: S.optionalKey(S.Record(S.String, DocumentMetadataValue)),
  })),
  knowledge: S.optionalKey(S.Struct({
    kgCores: S.optionalKey(S.Array(S.String).pipe(S.mutable)),
    deCores: S.optionalKey(S.Array(S.String).pipe(S.mutable)),
    loadedKgCores: S.optionalKey(S.Array(S.String).pipe(S.mutable)),
  })),
  collections: S.optionalKey(S.Array(UnknownRecord).pipe(S.mutable)),
  graph: S.optionalKey(S.Struct({
    triplesByFlowCollection: S.optionalKey(S.Record(S.String, S.Array(ClientTriple).pipe(S.mutable))),
    explainTriplesByGraph: S.optionalKey(S.Record(S.String, S.Array(ClientTriple).pipe(S.mutable))),
  })),
  chat: S.optionalKey(S.Struct({
    delayFrames: S.optionalKey(S.Finite),
  })),
}, { description: "Seed fixture for deterministic workbench QA runs." }) {}

interface UploadSession {
  readonly metadata: DocumentMetadata;
  readonly chunks: string[];
  readonly totalSize: number;
  readonly chunkSize: number;
  readonly totalChunks: number;
}

interface MockState {
  readonly settings: Required<NonNullable<MockWorkbenchFixture["settings"]>>;
  readonly flows: {
    readonly activeIds: string[];
    readonly definitions: Record<string, Record<string, unknown>>;
    readonly blueprints: Record<string, Record<string, unknown>>;
  };
  readonly config: {
    readonly prompt: Record<string, unknown>;
    readonly valuesByType: ConfigValues;
  };
  readonly library: {
    readonly documents: DocumentMetadata[];
    readonly processing: ProcessingMetadata[];
    readonly metadataById: Record<string, DocumentMetadata>;
    readonly uploads: Record<string, UploadSession>;
  };
  readonly knowledge: {
    readonly kgCores: string[];
    readonly deCores: string[];
    readonly loadedKgCores: string[];
  };
  readonly collections: Array<Record<string, unknown>>;
  readonly graph: {
    readonly triplesByFlowCollection: Record<string, Triple[]>;
    readonly explainTriplesByGraph: Record<string, Triple[]>;
  };
  readonly chat: {
    readonly delayFrames: number;
  };
}

const encodeJsonUnknown = S.encodeUnknownOption(S.fromJsonString(S.Unknown));
const decodeJsonUnknown = S.decodeUnknownOption(S.UnknownFromJsonString);

const iri = (value: string) => ({ t: "i" as const, i: value });
const literal = (value: string) => ({ t: "l" as const, v: value });

function encodeJson(value: unknown): string {
  return Option.getOrElse(encodeJsonUnknown(value), () => "{}");
}

function decodeJson(value: unknown): unknown {
  if (typeof value !== "string") return value;
  return Option.getOrElse(decodeJsonUnknown(value), () => value);
}

function asRecord(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === "object" ? value as Record<string, unknown> : {};
}

function stringValue(value: unknown, fallback = ""): string {
  return typeof value === "string" && value.length > 0 ? value : fallback;
}

function numberValue(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function withDefaultCollection(value: unknown): string {
  return stringValue(value, "default");
}

function graphKey(flow: string | undefined, collection: unknown): string {
  return `${flow ?? "default"}:${withDefaultCollection(collection)}`;
}

function cloneArray<A>(items: readonly A[] | undefined): A[] {
  return items === undefined ? [] : [...items];
}

function defaultConfigValues(): ConfigValues {
  return {
    mcp: {
      "qa-search": encodeJson({
        url: "http://localhost:8383/mcp",
        "remote-name": "qa-search",
        "auth-token": "qa-token",
      }),
    },
    tool: {
      "qa-search-tool": encodeJson({
        type: "mcp-tool",
        name: "QA Search",
        description: "Search tool used by browser QA",
        "mcp-tool": "qa-search",
        group: ["default"],
        arguments: [{ name: "query", type: "string", description: "Search query" }],
      }),
    },
    "token-cost": {
      "qa-model": encodeJson({ input_price: 1.25, output_price: 2.5 }),
    },
  };
}

function defaultTriples(): Triple[] {
  return [
    { s: iri("https://example.test/Alice"), p: iri("http://www.w3.org/2000/01/rdf-schema#label"), o: literal("Alice") },
    { s: iri("https://example.test/Bob"), p: iri("http://www.w3.org/2000/01/rdf-schema#label"), o: literal("Bob") },
    { s: iri("https://example.test/Acme"), p: iri("http://www.w3.org/2000/01/rdf-schema#label"), o: literal("Acme") },
    { s: iri("https://example.test/Alice"), p: iri("https://schema.org/worksFor"), o: iri("https://example.test/Acme") },
    { s: iri("https://example.test/Alice"), p: iri("https://schema.org/knows"), o: iri("https://example.test/Bob") },
  ];
}

function createState(fixture: MockWorkbenchFixture = {}): MockState {
  const documents = cloneArray(fixture.library?.documents);
  const defaultDocument: DocumentMetadata = {
    id: "qa-doc-1",
    title: "QA Document",
    kind: "text/plain",
    comments: "Seeded document for browser QA",
    tags: ["qa", "seed"],
    time: 1_700_000_000,
    user: "qa-user",
    "document-type": "source",
    documentType: "source",
  };
  if (documents.length === 0) documents.push(defaultDocument);

  const metadataById: Record<string, DocumentMetadata> = {
    [defaultDocument.id ?? "qa-doc-1"]: defaultDocument,
    ...(fixture.library?.metadataById ?? {}),
  };
  for (const document of documents) {
    if (document.id !== undefined) metadataById[document.id] = document;
  }

  const triples = defaultTriples();
  return {
    settings: {
      user: fixture.settings?.user ?? "qa-user",
      apiKey: fixture.settings?.apiKey ?? "",
      gatewayUrl: fixture.settings?.gatewayUrl ?? "",
      collection: fixture.settings?.collection ?? "default",
      featureSwitches: {
        flowClasses: true,
        submissions: true,
        tokenCost: true,
        schemas: true,
        structuredQuery: true,
        ontologyEditor: true,
        agentTools: true,
        mcpTools: true,
        llmModels: true,
        ...(fixture.settings?.featureSwitches ?? {}),
      },
    },
    flows: {
      activeIds: cloneArray(fixture.flows?.activeIds).length > 0 ? cloneArray(fixture.flows?.activeIds) : ["default", "qa-flow"],
      definitions: {
        default: { id: "default", description: "Default QA flow", class: "qa.default" },
        "qa-flow": { id: "qa-flow", description: "Seeded QA flow", class: "qa.seed" },
        ...(fixture.flows?.definitions ?? {}),
      },
      blueprints: {
        "qa-blueprint": {
          name: "qa-blueprint",
          description: "Blueprint used by browser QA",
          parameters: { temperature: { type: "number", default: 0.1 } },
        },
        ...(fixture.flows?.blueprints ?? {}),
      },
    },
    config: {
      prompt: {
        system: "You are the QA system prompt.",
        "qa-template": {
          system: "QA template system",
          prompt: "Answer the QA question: {{question}}",
        },
        ...(fixture.config?.prompt ?? {}),
      },
      valuesByType: {
        ...defaultConfigValues(),
        ...(fixture.config?.valuesByType ?? {}),
      },
    },
    library: {
      documents,
      processing: cloneArray(fixture.library?.processing),
      metadataById,
      uploads: {},
    },
    knowledge: {
      kgCores: cloneArray(fixture.knowledge?.kgCores).length > 0 ? cloneArray(fixture.knowledge?.kgCores) : ["qa-core"],
      deCores: cloneArray(fixture.knowledge?.deCores).length > 0 ? cloneArray(fixture.knowledge?.deCores) : ["qa-de-core"],
      loadedKgCores: cloneArray(fixture.knowledge?.loadedKgCores),
    },
    collections: cloneArray(fixture.collections).length > 0
      ? cloneArray(fixture.collections)
      : [{ id: "default", collection: "default", name: "default" }, { id: "qa-collection", collection: "qa-collection", name: "QA Collection" }],
    graph: {
      triplesByFlowCollection: {
        "default:default": triples,
        "qa-flow:default": triples,
        ...(fixture.graph?.triplesByFlowCollection ?? {}),
      },
      explainTriplesByGraph: {
        "urn:qa-explain": triples.slice(0, 3),
        ...(fixture.graph?.explainTriplesByGraph ?? {}),
      },
    },
    chat: {
      delayFrames: fixture.chat?.delayFrames ?? 0,
    },
  };
}

function configValues(state: MockState, type: string) {
  return Object.entries(state.config.valuesByType[type] ?? {}).map(([key, value]) => ({
    type,
    key,
    value: typeof value === "string" ? value : encodeJson(value),
  }));
}

function addDocument(state: MockState, metadata: DocumentMetadata): DocumentMetadata {
  const id = metadata.id ?? `qa-doc-${state.library.documents.length + 1}`;
  const currentTimeSeconds = state.library.documents.length + 1;
  const document = {
    ...metadata,
    id,
    title: metadata.title ?? id,
    kind: metadata.kind ?? metadata["document-type"] ?? "text/plain",
    time: metadata.time ?? currentTimeSeconds,
    user: metadata.user ?? state.settings.user,
    tags: metadata.tags ?? [],
  };
  state.library.documents.push(document);
  state.library.metadataById[id] = document;
  return document;
}

function dispatchRequest(state: MockState, service: string, request: Record<string, unknown>, flow: string | undefined): unknown {
  return Match.value(service).pipe(
    Match.when("flow", () => dispatchFlow(state, request)),
    Match.when("config", () => dispatchConfig(state, request)),
    Match.when("librarian", () => dispatchLibrarian(state, request)),
    Match.when("knowledge", () => dispatchKnowledge(state, request)),
    Match.when("collection-management", () => dispatchCollections(state, request)),
    Match.when("triples", () => dispatchTriples(state, request, flow)),
    Match.orElse(() => ({})),
  );
}

function dispatchFlow(state: MockState, request: Record<string, unknown>): unknown {
  const operation = request.operation;
  if (operation === "list-flows") return { "flow-ids": [...state.flows.activeIds] };
  if (operation === "get-flow") {
    const id = stringValue(request["flow-id"], "default");
    return { flow: encodeJson(state.flows.definitions[id] ?? { id, description: "Mock flow" }) };
  }
  if (operation === "list-blueprints") {
    return { "blueprint-names": A.sort(Object.keys(state.flows.blueprints), Order.String) };
  }
  if (operation === "get-blueprint") {
    const name = stringValue(request["blueprint-name"], "qa-blueprint");
    return { "blueprint-definition": encodeJson(state.flows.blueprints[name] ?? {}) };
  }
  if (operation === "start-flow") {
    const id = stringValue(request["flow-id"], `qa-flow-${state.flows.activeIds.length + 1}`);
    if (!state.flows.activeIds.includes(id)) state.flows.activeIds.push(id);
    state.flows.definitions[id] = {
      id,
      description: stringValue(request.description, "QA flow"),
      blueprint: stringValue(request["blueprint-name"], "qa-blueprint"),
      parameters: asRecord(request.parameters),
    };
    state.graph.triplesByFlowCollection[`${id}:default`] = defaultTriples();
    return {};
  }
  if (operation === "stop-flow") {
    const id = stringValue(request["flow-id"]);
    state.flows.activeIds.splice(0, state.flows.activeIds.length, ...state.flows.activeIds.filter((flowId) => flowId !== id));
    return {};
  }
  return {};
}

function dispatchConfig(state: MockState, request: Record<string, unknown>): unknown {
  const operation = request.operation;
  if (operation === "config") return { config: { prompt: state.config.prompt } };
  if (operation === "getvalues") return { values: configValues(state, stringValue(request.type)) };
  if (operation === "list") {
    const type = stringValue(request.type);
    return { keys: Object.keys(state.config.valuesByType[type] ?? {}) };
  }
  if (operation === "put" && Array.isArray(request.values)) {
    for (const value of request.values) {
      const item = asRecord(value);
      const type = stringValue(item.type);
      const key = stringValue(item.key);
      if (type.length > 0 && key.length > 0) {
        state.config.valuesByType[type] = state.config.valuesByType[type] ?? {};
        state.config.valuesByType[type][key] = item.value;
      }
    }
    return {};
  }
  if (operation === "delete" && Array.isArray(request.keys)) {
    for (const value of request.keys) {
      const item = asRecord(value);
      const type = stringValue(item.type);
      const key = stringValue(item.key);
      delete state.config.valuesByType[type]?.[key];
    }
    return {};
  }
  return {};
}

function dispatchLibrarian(state: MockState, request: Record<string, unknown>): unknown {
  const operation = request.operation;
  if (operation === "list-documents") return { "document-metadatas": [...state.library.documents] };
  if (operation === "list-processing") return { "processing-metadatas": [...state.library.processing] };
  if (operation === "get-document-metadata") {
    const id = stringValue(request["document-id"] ?? request.documentId);
    return { "document-metadata": state.library.metadataById[id] ?? null };
  }
  if (operation === "add-document") {
    addDocument(state, asRecord(request["document-metadata"] ?? request.documentMetadata) as DocumentMetadata);
    return {};
  }
  if (operation === "remove-document") {
    const id = stringValue(request["document-id"] ?? request.documentId);
    state.library.documents.splice(0, state.library.documents.length, ...state.library.documents.filter((document) => document.id !== id));
    delete state.library.metadataById[id];
    return {};
  }
  if (operation === "begin-upload") {
    const totalSize = numberValue(request["total-size"], 0);
    const chunkSize = Math.max(256_000, numberValue(request["chunk-size"], 512_000));
    const totalChunks = Math.max(1, Math.ceil(totalSize / chunkSize));
    const uploadId = `qa-upload-${Object.keys(state.library.uploads).length + 1}`;
    state.library.uploads[uploadId] = {
      metadata: asRecord(request["document-metadata"] ?? request.documentMetadata) as DocumentMetadata,
      chunks: [],
      totalSize,
      chunkSize,
      totalChunks,
    };
    return { "upload-id": uploadId, "chunk-size": chunkSize, "total-chunks": totalChunks };
  }
  if (operation === "upload-chunk") {
    const uploadId = stringValue(request["upload-id"]);
    const chunkIndex = numberValue(request["chunk-index"], 0);
    const upload = state.library.uploads[uploadId];
    if (upload !== undefined) upload.chunks[chunkIndex] = stringValue(request.content);
    return { "chunks-received": upload?.chunks.filter((chunk) => chunk !== undefined).length ?? 0 };
  }
  if (operation === "complete-upload") {
    const uploadId = stringValue(request["upload-id"]);
    const upload = state.library.uploads[uploadId];
    if (upload !== undefined) {
      addDocument(state, { ...upload.metadata, id: upload.metadata.id ?? uploadId });
      delete state.library.uploads[uploadId];
    }
    return { "document-id": uploadId, "object-id": uploadId };
  }
  return {};
}

function dispatchKnowledge(state: MockState, request: Record<string, unknown>): unknown {
  const operation = request.operation;
  const id = stringValue(request.id);
  if (operation === "list-kg-cores") return { ids: [...state.knowledge.kgCores] };
  if (operation === "list-de-cores") return { ids: [...state.knowledge.deCores] };
  if (operation === "load-kg-core") {
    if (id.length > 0 && !state.knowledge.loadedKgCores.includes(id)) state.knowledge.loadedKgCores.push(id);
    return {};
  }
  if (operation === "delete-kg-core") {
    state.knowledge.kgCores.splice(0, state.knowledge.kgCores.length, ...state.knowledge.kgCores.filter((core) => core !== id));
    return {};
  }
  return {};
}

function dispatchCollections(state: MockState, request: Record<string, unknown>): unknown {
  const operation = request.operation;
  const collection = stringValue(request.collection, "default");
  if (operation === "list-collections") return { collections: [...state.collections] };
  if (operation === "update-collection") {
    const entry = {
      id: collection,
      collection,
      name: stringValue(request.name, collection),
      description: stringValue(request.description),
      tags: Array.isArray(request.tags) ? request.tags : [],
    };
    state.collections.splice(0, state.collections.length, ...state.collections.filter((item) => item.collection !== collection && item.id !== collection), entry);
    return { collections: [entry] };
  }
  if (operation === "delete-collection") {
    state.collections.splice(0, state.collections.length, ...state.collections.filter((item) => item.collection !== collection && item.id !== collection));
    return {};
  }
  return {};
}

function dispatchTriples(state: MockState, request: Record<string, unknown>, flow: string | undefined): unknown {
  const graph = stringValue(request.g);
  const triples = graph.length > 0
    ? state.graph.explainTriplesByGraph[graph] ?? []
    : state.graph.triplesByFlowCollection[graphKey(flow, request.collection)] ?? [];
  return { triples: triples.slice(0, numberValue(request.limit, triples.length)) };
}

function streamResponses(service: string): Record<string, unknown>[] {
  const metadata: StreamingMetadata = { model: "qa-model", in_token: 12, out_token: 24 };
  if (service === "agent") {
    return [
      { chunk_type: "thought", content: "Thinking about the QA request.", end_of_message: true },
      { chunk_type: "observation", content: "Observed seeded graph and document context.", end_of_message: true },
      { chunk_type: "answer", content: "Mock agent answer from TrustGraph.", end_of_message: true, end_of_dialog: true, ...metadata },
    ];
  }
  if (service === "document-rag") {
    return [
      { message_type: "explain", explain_id: "qa-document-explain", explain_graph: "urn:qa-explain" },
      { response: "Mock document answer ", end_of_session: false },
      { response: "from QA library.", end_of_session: true, ...metadata },
    ];
  }
  return [
    { message_type: "explain", explain_id: "qa-graph-explain", explain_graph: "urn:qa-explain" },
    { response: "Mock graph answer ", end_of_session: false },
    { response: "from QA knowledge graph.", end_of_session: true, ...metadata },
  ];
}

function scheduleFrames(frames: number, callback: () => void): void {
  const schedule = typeof requestAnimationFrame === "function" ? requestAnimationFrame : (fn: FrameRequestCallback) => queueMicrotask(() => fn(0));
  if (frames <= 0) {
    schedule(callback);
  } else {
    schedule(() => scheduleFrames(frames - 1, callback));
  }
}

function dispatchStream<ResponseType>(
  state: MockState,
  service: string,
  receiver: (resp: unknown) => boolean,
): Promise<ResponseType> {
  const responses = streamResponses(service);
  const emit = (index: number) => {
    const response = responses[index];
    if (response === undefined) return;
    const complete = index === responses.length - 1;
    const done = receiver({ response, complete });
    if (done !== true && !complete) {
      scheduleFrames(state.chat.delayFrames, () => emit(index + 1));
    }
  };
  scheduleFrames(state.chat.delayFrames, () => emit(0));
  return Promise.resolve({} as ResponseType);
}

export function makeMockBaseApi(fixture: MockWorkbenchFixture = {}): WorkbenchQaApi {
  const state = createState(fixture);
  return {
    makeRequest: <RequestType extends object, ResponseType>(
      service: string,
      request: RequestType,
      _timeout?: number,
      _retries?: number,
      flow?: string,
    ): Promise<ResponseType> =>
      Promise.resolve(
        dispatchRequest(
          state,
          service,
          request as Record<string, unknown>,
          flow,
        ) as ResponseType,
      ),
    makeRequestMulti: <RequestType extends object, ResponseType>(
      service: string,
      _request: RequestType,
      receiver: (resp: unknown) => boolean,
    ): Promise<ResponseType> =>
      dispatchStream(state, service, (message) => {
        const chunk = message as { response?: unknown; complete?: boolean };
        return receiver({
          response: chunk.response,
          complete: chunk.complete === true,
        });
      }).then(() => ({}) as ResponseType),
  };
}

export function qaSettingsFromFixture(fixture: MockWorkbenchFixture = {}) {
  return createState(fixture).settings;
}

export function decodeConfigFixtureValue(value: unknown): unknown {
  return decodeJson(value);
}
