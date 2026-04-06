import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { SectionLabel, SearchInput, ExplainGraph } from "../components";
import type { ExplainGraphNode, ExplainGraphEdge } from "../components";
import { COLLECTION } from "../config";
import { useInference } from "@trustgraph/react-state";
import type { ExplainEvent, Triple, Term } from "@trustgraph/react-state";
import { useSocket } from "@trustgraph/react-provider";
import type { BaseApi } from "@trustgraph/react-provider";
import { palette, text, border, withGlow, semantic } from "../theme";

// ── Namespaces ──────────────────────────────────────────────────────
const TG = "https://trustgraph.ai/ns/";
const TG_QUERY = TG + "query";
const TG_CONCEPT = TG + "concept";
const TG_ENTITY = TG + "entity";
const TG_EDGE_COUNT = TG + "edgeCount";
const TG_SELECTED_EDGE = TG + "selectedEdge";
const TG_EDGE = TG + "edge";
const TG_REASONING = TG + "reasoning";
const TG_CONTENT = TG + "content";
const TG_CONTAINS = TG + "contains";
const TG_CHUNK_COUNT = TG + "chunkCount";
const TG_ACTION = TG + "action";
const TG_ARGUMENTS = TG + "arguments";
const TG_THOUGHT = TG + "thought";
const TG_OBSERVATION = TG + "observation";
const TG_DOCUMENT = TG + "document";
const RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type";
const PROV = "http://www.w3.org/ns/prov#";
const PROV_STARTED_AT_TIME = PROV + "startedAtTime";
const PROV_WAS_DERIVED_FROM = PROV + "wasDerivedFrom";
const RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label";

// ── Types ───────────────────────────────────────────────────────────

interface EdgeSelection {
  edgeUri: string;
  edge?: { s: string; p: string; o: string };
  edgeLabels?: { s: string; p: string; o: string };
  reasoning?: string;
  sources?: ProvenanceChain[];
}

interface ProvenanceChain {
  chain: { uri: string; label: string }[];
}

interface QuestionData {
  query?: string;
  timestamp?: string;
}

interface GroundingData {
  concepts: string[];
}

interface ExplorationData {
  edgeCount?: string;
  chunkCount?: string;
  entities: string[];
  entityLabels?: string[];
}

interface FocusData {
  edgeSelections: EdgeSelection[];
}

interface SynthesisData {
  contentLength?: number;
}

interface AnalysisData {
  action?: string;
  arguments?: string;
  thoughtUri?: string;
  observationUri?: string;
}

interface ConclusionData {
  documentUri?: string;
}

interface ReflectionData {
  documentUri?: string;
  reflectionType?: string;
}

type EventData = QuestionData | GroundingData | ExplorationData | FocusData | SynthesisData | AnalysisData | ConclusionData | ReflectionData;

interface SourcePanelState {
  chunkUri: string;
  documentUri: string;
  documentTitle?: string;
  documentTags?: string[];
  chunkText?: string;
  loading: boolean;
  error?: string;
}

interface ExplainNode {
  explainId: string;
  explainGraph: string;
  eventType: string;
  data?: EventData;
  fetched: boolean;
  fetching: boolean;
  error?: string;
}

// ── Helpers ─────────────────────────────────────────────────────────

function shortUri(uri: string): string {
  if (uri.startsWith("urn:trustgraph:prov:")) return "tg:prov:" + uri.slice(20);
  if (uri.startsWith("urn:trustgraph:")) return "tg:" + uri.slice(15);
  if (uri.startsWith(TG)) return "tg:" + uri.slice(TG.length);
  if (uri.startsWith(PROV)) return "prov:" + uri.slice(PROV.length);
  if (uri.startsWith("http://www.w3.org/2000/01/rdf-schema#")) return "rdfs:" + uri.slice(37);
  if (uri.startsWith("http://www.w3.org/1999/02/22-rdf-syntax-ns#")) return "rdf:" + uri.slice(43);
  if (uri.startsWith("urn:")) return uri;
  const pos = Math.max(uri.lastIndexOf("#"), uri.lastIndexOf("/"));
  return pos >= 0 ? uri.slice(pos + 1) : uri;
}

// Ordered type checks — mirrors the Python ExplainEntity.from_triples logic.
// Each entry: [type URI to look for, display name].
// First match wins.
const TYPE_CHECKS: [string, string][] = [
  [TG + "GraphRagQuestion", "question"],
  [TG + "DocRagQuestion", "question"],
  [TG + "AgentQuestion", "question"],
  [TG + "Question", "question"],
  [TG + "Grounding", "grounding"],
  [TG + "Exploration", "exploration"],
  [TG + "Focus", "focus"],
  [TG + "Synthesis", "synthesis"],
  [TG + "Reflection", "reflection"],
  [TG + "Thought", "reflection"],
  [TG + "Observation", "reflection"],
  [TG + "Analysis", "analysis"],
  [TG + "Conclusion", "conclusion"],
];

function getEventTypeFromTriples(triples: Triple[]): string {
  const types = new Set<string>();
  for (const t of triples) {
    if (predIri(t) === RDF_TYPE) types.add(objValue(t));
  }
  for (const [typeUri, displayName] of TYPE_CHECKS) {
    if (types.has(typeUri)) return displayName;
  }
  return "unknown";
}

function eventTypeColor(eventType: string): string {
  switch (eventType) {
    case "question": return palette.amber;
    case "grounding": return palette.orange;
    case "exploration": return palette.blue;
    case "focus": return palette.purple;
    case "analysis": return palette.purple;
    case "reflection": return palette.cyan;
    case "synthesis": return palette.emerald;
    case "conclusion": return palette.emerald;
    default: return text.muted;
  }
}

// Get predicate IRI from a triple
function predIri(triple: Triple): string {
  return triple.p.t === "i" ? triple.p.i : "";
}

// Get object value (string) from a triple
function objValue(triple: Triple): string {
  const o = triple.o;
  if (o.t === "i") return o.i;
  if (o.t === "l") return o.v;
  if (o.t === "b") return o.d;
  return "";
}

// Get object as quoted triple {s, p, o} if it's a triple term
function objQuotedTriple(triple: Triple): { s: string; p: string; o: string } | null {
  const o = triple.o;
  if (o.t === "t" && o.tr) {
    return {
      s: o.tr.s.t === "i" ? o.tr.s.i : (o.tr.s as any).v || "",
      p: o.tr.p.t === "i" ? o.tr.p.i : (o.tr.p as any).v || "",
      o: o.tr.o.t === "i" ? o.tr.o.i : (o.tr.o as any).v || "",
    };
  }
  return null;
}

// ── KG query helpers (using the socket API) ─────────────────────────

async function queryTriples(
  api: ReturnType<BaseApi["flow"]>,
  subject: string,
  predicate?: string,
  limit = 100,
  collection = COLLECTION,
  graph?: string,
): Promise<Triple[]> {
  const s: Term = { t: "i", i: subject };
  const p: Term | undefined = predicate ? { t: "i", i: predicate } : undefined;
  return api.triplesQuery(s, p, undefined, limit, collection, graph);
}

// Backoff retry for eventually-consistent event triples.
// Calls onUpdate each time new triples arrive, settles when two consecutive
// fetches return the same count, or after maxTries (6 = 1 initial + 5 retries).
// Backoff: 50ms × 3 each retry, capped at 1500ms.
async function queryTriplesUntilSettled(
  api: ReturnType<BaseApi["flow"]>,
  subject: string,
  onUpdate: (triples: Triple[]) => void,
  limit = 100,
  collection = COLLECTION,
  graph?: string,
  maxTries = 6,
): Promise<Triple[]> {
  let prevCount = -1;
  let settled: Triple[] = [];
  let delay = 50;

  for (let attempt = 0; attempt < maxTries; attempt++) {
    const triples = await queryTriples(api, subject, undefined, limit, collection, graph);

    if (triples.length !== prevCount) {
      settled = triples;
      onUpdate(triples);
    } else {
      // Two consecutive identical counts — settled
      return settled;
    }

    prevCount = triples.length;

    if (attempt < maxTries - 1) {
      await new Promise(r => setTimeout(r, delay));
      delay = Math.min(delay * 3, 1500);
    }
  }

  return settled;
}

// Resolve rdfs:label for a URI, with cache
async function resolveLabel(
  api: ReturnType<BaseApi["flow"]>,
  uri: string,
  cache: Map<string, string>,
): Promise<string> {
  if (cache.has(uri)) return cache.get(uri)!;
  try {
    const triples = await api.triplesQuery(
      { t: "i", i: uri },
      { t: "i", i: RDFS_LABEL },
      undefined,
      1,
      COLLECTION,
    );
    const label = triples.length > 0 ? objValue(triples[0]) : shortUri(uri);
    cache.set(uri, label);
    return label;
  } catch {
    const fallback = shortUri(uri);
    cache.set(uri, fallback);
    return fallback;
  }
}

// Trace prov:wasDerivedFrom chain up to root
async function traceProvenanceChain(
  api: ReturnType<BaseApi["flow"]>,
  startUri: string,
  labelCache: Map<string, string>,
  maxDepth = 10,
): Promise<ProvenanceChain> {
  const chain: { uri: string; label: string }[] = [];
  let current: string | null = startUri;

  for (let i = 0; i < maxDepth && current; i++) {
    const label = await resolveLabel(api, current, labelCache);
    chain.push({ uri: current, label });

    // Find parent
    const parentTriples = await api.triplesQuery(
      { t: "i", i: current },
      { t: "i", i: PROV_WAS_DERIVED_FROM },
      undefined,
      1,
      COLLECTION,
    );

    const parentUri = parentTriples.length > 0 ? objValue(parentTriples[0]) : null;
    if (!parentUri || parentUri === current) break;
    current = parentUri;
  }

  return { chain };
}

// Query edge provenance: find subgraphs containing the edge via tg:contains
async function queryEdgeProvenance(
  api: ReturnType<BaseApi["flow"]>,
  edge: { s: string; p: string; o: string },
  labelCache: Map<string, string>,
): Promise<ProvenanceChain[]> {
  // Find subgraphs that contain this edge: ?subgraph tg:contains <<s p o>>
  const oTerm: Term = (edge.o.startsWith("http") || edge.o.startsWith("urn:"))
    ? { t: "i", i: edge.o }
    : { t: "l", v: edge.o };

  const containsTriples = await api.triplesQuery(
    undefined,
    { t: "i", i: TG_CONTAINS },
    {
      t: "t",
      tr: {
        s: { t: "i", i: edge.s },
        p: { t: "i", i: edge.p },
        o: oTerm,
      },
    },
    10,
    COLLECTION,
  );

  // For each subgraph, follow wasDerivedFrom to sources
  const chains: ProvenanceChain[] = [];
  for (const t of containsTriples) {
    const subgraphUri = t.s.t === "i" ? t.s.i : "";
    if (!subgraphUri) continue;

    const derivedTriples = await api.triplesQuery(
      { t: "i", i: subgraphUri },
      { t: "i", i: PROV_WAS_DERIVED_FROM },
      undefined,
      10,
      COLLECTION,
    );

    for (const dt of derivedTriples) {
      const sourceUri = objValue(dt);
      if (sourceUri) {
        const chain = await traceProvenanceChain(api, sourceUri, labelCache);
        chains.push(chain);
      }
    }
  }

  return chains;
}

// ── Parse basic event data (synchronous, from already-fetched triples) ──

function parseBasicEventData(eventType: string, triples: Triple[]): EventData {
  switch (eventType) {
    case "question": {
      const data: QuestionData = {};
      for (const t of triples) {
        const p = predIri(t);
        if (p === TG_QUERY) data.query = objValue(t);
        if (p === PROV_STARTED_AT_TIME) data.timestamp = objValue(t);
      }
      return data;
    }

    case "grounding": {
      const concepts: string[] = [];
      for (const t of triples) {
        if (predIri(t) === TG_CONCEPT) {
          const v = objValue(t);
          if (v) concepts.push(v);
        }
      }
      return { concepts } as GroundingData;
    }

    case "exploration": {
      const data: ExplorationData = { entities: [] };
      for (const t of triples) {
        const p = predIri(t);
        if (p === TG_EDGE_COUNT) data.edgeCount = objValue(t);
        if (p === TG_CHUNK_COUNT) data.chunkCount = objValue(t);
        if (p === TG_ENTITY) {
          const uri = objValue(t);
          if (uri) data.entities.push(uri);
        }
      }
      return data;
    }

    case "focus": {
      const edgeSelUris: string[] = [];
      for (const t of triples) {
        if (predIri(t) === TG_SELECTED_EDGE) {
          const uri = objValue(t);
          if (uri) edgeSelUris.push(uri);
        }
      }
      return {
        edgeSelections: edgeSelUris.map(uri => ({ edgeUri: uri })),
      } as FocusData;
    }

    case "synthesis": {
      const data: SynthesisData = {};
      for (const t of triples) {
        if (predIri(t) === TG_CONTENT) {
          data.contentLength = objValue(t).length;
        }
      }
      return data;
    }

    case "analysis": {
      const data: AnalysisData = {};
      for (const t of triples) {
        const p = predIri(t);
        if (p === TG_ACTION) data.action = objValue(t);
        if (p === TG_ARGUMENTS) data.arguments = objValue(t);
        if (p === TG_THOUGHT) data.thoughtUri = objValue(t);
        if (p === TG_OBSERVATION) data.observationUri = objValue(t);
      }
      return data;
    }

    case "conclusion": {
      const data: ConclusionData = {};
      for (const t of triples) {
        if (predIri(t) === TG_DOCUMENT) data.documentUri = objValue(t);
      }
      return data;
    }

    case "reflection": {
      const data: ReflectionData = {};
      for (const t of triples) {
        if (predIri(t) === TG_DOCUMENT) data.documentUri = objValue(t);
      }
      return data;
    }

    default:
      return {};
  }
}

// ── Enrich event data (async — labels, edge details, provenance) ────

async function enrichEventData(
  api: ReturnType<BaseApi["flow"]>,
  eventType: string,
  _triples: Triple[],
  basicData: EventData,
  labelCache: Map<string, string>,
  explainGraph: string,
): Promise<EventData> {
  switch (eventType) {
    case "exploration": {
      const data = { ...(basicData as ExplorationData) };
      if (data.entities.length > 0) {
        data.entityLabels = await Promise.all(
          data.entities.map(uri => resolveLabel(api, uri, labelCache))
        );
      }
      return data;
    }

    case "focus": {
      const basic = basicData as FocusData;
      const edgeSelections = await Promise.all(basic.edgeSelections.map(async (basicSel) => {
        const edgeTriples = await queryTriples(
          api, basicSel.edgeUri, undefined, 100, COLLECTION, explainGraph,
        );

        const sel: EdgeSelection = { edgeUri: basicSel.edgeUri };
        for (const et of edgeTriples) {
          const p = predIri(et);
          if (p === TG_EDGE) sel.edge = objQuotedTriple(et) || undefined;
          if (p === TG_REASONING) sel.reasoning = objValue(et);
        }

        if (sel.edge) {
          const [labels, sources] = await Promise.all([
            Promise.all([
              resolveLabel(api, sel.edge.s, labelCache),
              resolveLabel(api, sel.edge.p, labelCache),
              resolveLabel(api, sel.edge.o, labelCache),
            ]),
            queryEdgeProvenance(api, sel.edge, labelCache),
          ]);
          sel.edgeLabels = { s: labels[0], p: labels[1], o: labels[2] };
          sel.sources = sources;
        }

        return sel;
      }));

      return { edgeSelections } as FocusData;
    }

    default:
      return basicData;
  }
}

// ── Component ───────────────────────────────────────────────────────

type QueryMode = "graph-rag" | "doc-rag" | "agent";

const queryModeLabels: Record<QueryMode, string> = {
  "graph-rag": "Graph RAG",
  "doc-rag": "Doc RAG",
  "agent": "Agent",
};

export function ExplainView() {
  const [input, setInput] = useState("");
  const [queryMode, setQueryMode] = useState<QueryMode>("graph-rag");
  const [response, setResponse] = useState("");
  const [agentMessages, setAgentMessages] = useState<{ type: string; text: string; done?: boolean }[]>([]);
  const [isQuerying, setIsQuerying] = useState(false);
  const [explainNodes, setExplainNodes] = useState<ExplainNode[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [highlightedNodeIds, setHighlightedNodeIds] = useState<string[]>([]);
  const [highlightedEdgeIds, setHighlightedEdgeIds] = useState<string[]>([]);
  const [sourcePanel, setSourcePanel] = useState<SourcePanelState | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const explainScrollRef = useRef<HTMLDivElement>(null);
  const labelCacheRef = useRef(new Map<string, string>());

  const { graphRag, documentRag, agent } = useInference({});
  const socket = useSocket();

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [response]);

  useEffect(() => {
    explainScrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [explainNodes]);

  // Fetch event data when new nodes arrive
  // Use a ref to access current nodes without re-rendering
  const nodesRef = useRef(explainNodes);
  nodesRef.current = explainNodes;

  const fetchNode = useCallback(async (explainId: string) => {
    setExplainNodes(prev => prev.map(n =>
      n.explainId === explainId ? { ...n, fetching: true } : n
    ));

    try {
      const api = socket.flow("default");
      const node = nodesRef.current.find(n => n.explainId === explainId);
      if (!node) return;

      const updateNode = (updates: Partial<ExplainNode>) => {
        setExplainNodes(prev => prev.map(n =>
          n.explainId === explainId ? { ...n, ...updates } : n
        ));
      };

      // Phase 1: Fetch event triples with backoff until settled.
      // These are eventually consistent — render progressively as they arrive.
      let latestEventType = "unknown";
      let latestBasicData: EventData = {};

      const settledTriples = await queryTriplesUntilSettled(
        api, node.explainId,
        (triples) => {
          latestEventType = getEventTypeFromTriples(triples);
          latestBasicData = parseBasicEventData(latestEventType, triples);
          updateNode({ eventType: latestEventType, data: latestBasicData, fetched: true, fetching: false });
        },
        100, COLLECTION, node.explainGraph,
      );

      if (settledTriples.length === 0) {
        updateNode({ fetched: true, fetching: false });
        return;
      }

      // Phase 2: Enrich with KG lookups (labels, edge details, provenance).
      // These reference known-to-exist data — no retry needed, just fetch once.
      const enriched = await enrichEventData(api, latestEventType, settledTriples, latestBasicData, labelCacheRef.current, node.explainGraph);
      if (enriched !== latestBasicData) {
        updateNode({ data: enriched });
      }
    } catch (err) {
      setExplainNodes(prev => prev.map(n =>
        n.explainId === explainId
          ? { ...n, error: String(err), fetching: false }
          : n
      ));
    }
  }, [socket]);

  useEffect(() => {
    for (const node of explainNodes) {
      if (!node.fetched && !node.fetching && !node.error) {
        fetchNode(node.explainId);
      }
    }
  }, [explainNodes, fetchNode]);

  const addExplainEvent = useCallback((event: ExplainEvent) => {
    setExplainNodes(prev => {
      if (prev.some(n => n.explainId === event.explainId)) return prev;
      return [...prev, {
        explainId: event.explainId,
        explainGraph: event.explainGraph,
        eventType: "unknown",
        fetched: false,
        fetching: false,
      }];
    });
  }, []);

  const handleSubmit = useCallback(async (query: string) => {
    if (!query.trim() || isQuerying) return;

    setIsQuerying(true);
    setResponse("");
    setAgentMessages([]);
    setExplainNodes([]);
    setHighlightedNodeIds([]);
    setHighlightedEdgeIds([]);
    setSourcePanel(null);
    setError(null);
    setInput("");
    labelCacheRef.current.clear();

    const trimmed = query.trim();

    try {
      switch (queryMode) {
        case "graph-rag": {
          await graphRag({
            input: trimmed,
            collection: COLLECTION,
            options: { maxSubgraphSize: 150 },
            callbacks: {
              onChunk: (chunk: string) => setResponse(prev => prev + chunk),
              onExplain: addExplainEvent,
              onError: (err: string) => setError(err),
            },
          });
          break;
        }

        case "doc-rag": {
          await documentRag({
            input: trimmed,
            collection: COLLECTION,
            callbacks: {
              onChunk: (chunk: string) => setResponse(prev => prev + chunk),
              onExplain: addExplainEvent,
              onError: (err: string) => setError(err),
            },
          });
          break;
        }

        case "agent": {
          // Track current streaming message per type
          const accum: Record<string, string> = {};

          const appendChunk = (type: string, chunk: string, complete?: boolean) => {
            accum[type] = (accum[type] || "") + chunk;
            const currentText = accum[type];
            setAgentMessages(prev => {
              // Find existing in-progress message of this type at end
              const lastIdx = prev.length - 1;
              if (lastIdx >= 0 && prev[lastIdx].type === type && !prev[lastIdx].done) {
                const updated = [...prev];
                updated[lastIdx] = { type, text: currentText, done: !!complete };
                return updated;
              }
              // New message
              return [...prev, { type, text: currentText, done: !!complete }];
            });
            if (complete) {
              accum[type] = "";
            }
          };

          await agent({
            input: trimmed,
            callbacks: {
              onThink: (chunk: string, complete?: boolean) => appendChunk("thinking", chunk, complete),
              onObserve: (chunk: string, complete?: boolean) => appendChunk("observation", chunk, complete),
              onAnswer: (chunk: string, complete?: boolean) => appendChunk("answer", chunk, complete),
              onExplain: addExplainEvent,
              onError: (err: string) => setError(err),
            },
          });
          break;
        }
      }
    } catch (err) {
      setError(String(err));
    } finally {
      setIsQuerying(false);
    }
  }, [graphRag, documentRag, agent, queryMode, isQuerying, addExplainEvent]);

  // ── Derive graph nodes and edges from explain events ──────────────
  const { graphNodes, graphEdges } = useMemo(() => {
    const nodeMap = new Map<string, ExplainGraphNode>();
    const edgeList: ExplainGraphEdge[] = [];

    for (const node of explainNodes) {
      if (!node.fetched || !node.data) continue;

      if (node.eventType === "exploration") {
        const d = node.data as ExplorationData;
        const labels = d.entityLabels || [];
        d.entities.forEach((uri, i) => {
          if (!nodeMap.has(uri)) {
            nodeMap.set(uri, { id: uri, label: labels[i] || shortUri(uri), color: palette.blue });
          }
        });
      }

      if (node.eventType === "focus") {
        const d = node.data as FocusData;
        for (const sel of d.edgeSelections) {
          if (!sel.edge) continue;
          const { s, p, o } = sel.edge;
          const sLabel = sel.edgeLabels?.s || shortUri(s);
          const pLabel = sel.edgeLabels?.p || shortUri(p);
          const oLabel = sel.edgeLabels?.o || shortUri(o);

          // Ensure nodes exist
          if (!nodeMap.has(s)) nodeMap.set(s, { id: s, label: sLabel, color: palette.pink });
          if (!nodeMap.has(o)) nodeMap.set(o, { id: o, label: oLabel, color: palette.pink });

          edgeList.push({
            id: sel.edgeUri,
            from: s,
            to: o,
            label: pLabel,
            reasoning: sel.reasoning,
          });
        }
      }
    }

    return { graphNodes: Array.from(nodeMap.values()), graphEdges: edgeList };
  }, [explainNodes]);

  // ── Entity/edge click → neighbourhood highlight on graph ─────────
  const handleEntityClick = useCallback((entityUri: string) => {
    // Highlight this node + connected edges + neighbour nodes
    const connectedEdges = graphEdges.filter(e => e.from === entityUri || e.to === entityUri);
    const neighbourIds = new Set<string>([entityUri]);
    const edgeIds: string[] = [];
    for (const e of connectedEdges) {
      edgeIds.push(e.id);
      neighbourIds.add(e.from);
      neighbourIds.add(e.to);
    }
    setHighlightedNodeIds(Array.from(neighbourIds));
    setHighlightedEdgeIds(edgeIds);
  }, [graphEdges]);

  const handleEdgeClick = useCallback((sel: EdgeSelection) => {
    // Highlight this edge + its two endpoint nodes
    const nodeIds: string[] = [];
    if (sel.edge) {
      nodeIds.push(sel.edge.s, sel.edge.o);
    }
    setHighlightedNodeIds(nodeIds);
    setHighlightedEdgeIds([sel.edgeUri]);
  }, []);

  const handleSourceClick = useCallback((source: ProvenanceChain) => {
    // chain[0] = chunk (closest to edge), chain[last] = root document
    const chunkNode = source.chain[0];
    const docNode = source.chain[source.chain.length - 1];
    if (!chunkNode || !docNode) return;

    // Same chunk — ignore (use the × button to close)
    if (sourcePanel?.chunkUri === chunkNode.uri) return;

    setSourcePanel({
      chunkUri: chunkNode.uri,
      documentUri: docNode.uri,
      loading: true,
    });

    const librarian = socket.librarian();

    // Fetch parent document metadata (title, tags) from librarian
    librarian.getDocumentMetadata(docNode.uri).then(meta => {
      setSourcePanel(prev => prev?.chunkUri === chunkNode.uri
        ? { ...prev, documentTitle: meta?.title, documentTags: meta?.tags }
        : prev
      );
    }).catch(() => {
      // Metadata not available — that's OK
    });

    // The chunk URI is itself a document ID in the librarian — stream it directly
    let chunkText = "";
    librarian.streamDocument(
      chunkNode.uri,
      (content, _chunkIndex, _totalChunks, complete) => {
        try {
          chunkText += atob(content);
        } catch {
          chunkText += content;
        }
        if (complete) {
          setSourcePanel(prev => prev?.chunkUri === chunkNode.uri
            ? { ...prev, chunkText, loading: false }
            : prev
          );
        }
      },
      (err) => {
        setSourcePanel(prev => prev?.chunkUri === chunkNode.uri
          ? { ...prev, loading: false, error: err }
          : prev
        );
      },
    );
  }, [socket, sourcePanel?.chunkUri]);

  return (
    <div style={{ display: "flex", height: "calc(100vh - 110px)" }}>
      {/* LHS: Query + Response */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", borderRight: `1px solid ${border.default}` }}>
        <div style={{ padding: "20px 28px", borderBottom: `1px solid ${border.default}` }}>
          <SectionLabel marginBottom={12}>{queryModeLabels[queryMode].toUpperCase()} QUERY</SectionLabel>
          <div style={{ display: "flex", gap: 4, marginBottom: 12 }}>
            {(["graph-rag", "doc-rag", "agent"] as QueryMode[]).map(mode => (
              <button
                key={mode}
                onClick={() => setQueryMode(mode)}
                disabled={isQuerying}
                style={{
                  padding: "5px 14px", borderRadius: 6, fontSize: 11,
                  fontFamily: "'IBM Plex Mono', monospace", fontWeight: 600,
                  cursor: isQuerying ? "default" : "pointer",
                  background: queryMode === mode ? withGlow(palette.cyan, 0.15) : "transparent",
                  border: `1px solid ${queryMode === mode ? withGlow(palette.cyan, 0.4) : border.default}`,
                  color: queryMode === mode ? palette.cyan : text.muted,
                  opacity: isQuerying ? 0.5 : 1,
                  transition: "all 0.15s ease",
                }}
              >
                {queryModeLabels[mode]}
              </button>
            ))}
          </div>
          <SearchInput
            value={input}
            onChange={setInput}
            onSubmit={() => handleSubmit(input)}
            placeholder="Ask a question..."
            buttonText="Query"
            isLoading={isQuerying}
            buttonColor={palette.cyan}
          />
        </div>

        <div style={{ flex: 1, padding: "24px 28px", overflowY: "auto" }}>
          {error && (
            <div style={{
              padding: "12px 16px", borderRadius: 10,
              background: withGlow(semantic.error, 0.08),
              border: `1px solid ${withGlow(semantic.error, 0.2)}`,
              marginBottom: 12,
            }}>
              <div style={{ fontSize: 10, color: withGlow(semantic.error, 0.53), fontFamily: "'IBM Plex Mono', monospace", marginBottom: 6 }}>ERROR</div>
              <div style={{ fontSize: 13, color: text.secondary, lineHeight: 1.6 }}>{error}</div>
            </div>
          )}

          {!response && !isQuerying && !error && agentMessages.length === 0 && (
            <div style={{ color: text.hint, fontSize: 13, fontStyle: "italic" }}>
              Ask a question to see {queryModeLabels[queryMode]} in action with live explainability.
            </div>
          )}

          {/* Streaming response for graph-rag and doc-rag */}
          {(response || (isQuerying && queryMode !== "agent")) && (
            <div>
              {response && (
                <div style={{
                  padding: "16px 20px", borderRadius: 10,
                  background: withGlow(semantic.answer, 0.08),
                  border: `1px solid ${withGlow(semantic.answer, 0.2)}`,
                }}>
                  <div style={{ fontSize: 10, color: withGlow(semantic.answer, 0.53), fontFamily: "'IBM Plex Mono', monospace", marginBottom: 8 }}>
                    <span style={{ color: semantic.answer }}>✓</span> RESPONSE
                  </div>
                  <div style={{ fontSize: 14, color: text.primary, lineHeight: 1.7, whiteSpace: "pre-wrap" }}>{response}</div>
                </div>
              )}
              {isQuerying && (
                <div style={{ padding: "8px 12px", fontSize: 11, color: withGlow(palette.cyan, 0.6), fontFamily: "'IBM Plex Mono', monospace", marginTop: 12 }}>
                  {response ? "Streaming..." : "Processing query..."}
                </div>
              )}
            </div>
          )}

          {/* Agent messages */}
          {queryMode === "agent" && agentMessages.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {agentMessages.map((msg, i) => {
                const colors: Record<string, string> = {
                  thinking: palette.purple,
                  observation: palette.blue,
                  answer: palette.emerald,
                };
                const color = colors[msg.type] || text.muted;
                return (
                  <div key={i} style={{
                    padding: "12px 16px", borderRadius: 10,
                    background: withGlow(color, 0.08),
                    border: `1px solid ${withGlow(color, 0.2)}`,
                  }}>
                    <div style={{ fontSize: 10, color: withGlow(color, 0.6), fontFamily: "'IBM Plex Mono', monospace", marginBottom: 6, textTransform: "uppercase", fontWeight: 600 }}>
                      {msg.type}
                    </div>
                    <div style={{ fontSize: 13, color: text.secondary, lineHeight: 1.6, whiteSpace: "pre-wrap" }}>{msg.text}</div>
                  </div>
                );
              })}
            </div>
          )}

          {queryMode === "agent" && isQuerying && agentMessages.length === 0 && (
            <div style={{ padding: "8px 12px", fontSize: 11, color: withGlow(palette.cyan, 0.6), fontFamily: "'IBM Plex Mono', monospace" }}>
              Agent is working...
            </div>
          )}

          <div ref={scrollRef} />
        </div>

        {/* Source text panel — shown when a provenance link is clicked */}
        {sourcePanel && (
          <div style={{
            maxHeight: "40%", borderTop: `1px solid ${border.default}`,
            display: "flex", flexDirection: "column",
            background: withGlow(palette.amber, 0.03),
          }}>
            {/* Header with document metadata */}
            <div style={{
              padding: "8px 16px", borderBottom: `1px solid ${border.default}`,
              display: "flex", alignItems: "center", justifyContent: "space-between",
            }}>
              <div style={{ fontSize: 11, fontFamily: "'IBM Plex Mono', monospace" }}>
                <span style={{ fontWeight: 600, color: palette.amber }}>SOURCE</span>
                {sourcePanel.documentTitle ? (
                  <span style={{ color: text.secondary, marginLeft: 8 }}>
                    {sourcePanel.documentTitle}
                  </span>
                ) : (
                  <span style={{ color: text.muted, marginLeft: 8 }}>
                    {shortUri(sourcePanel.documentUri)}
                  </span>
                )}
                {sourcePanel.documentTags && sourcePanel.documentTags.length > 0 && (
                  <span style={{ marginLeft: 8 }}>
                    {sourcePanel.documentTags.map((tag, i) => (
                      <span key={i} style={{
                        fontSize: 9, padding: "1px 6px", borderRadius: 3, marginLeft: 4,
                        background: withGlow(palette.cyan, 0.1),
                        border: `1px solid ${withGlow(palette.cyan, 0.2)}`,
                        color: text.subtle,
                      }}>
                        {tag}
                      </span>
                    ))}
                  </span>
                )}
              </div>
              <button
                onClick={() => setSourcePanel(null)}
                style={{
                  background: "none", border: "none", cursor: "pointer",
                  color: text.muted, fontSize: 16, padding: "0 4px",
                  lineHeight: 1,
                }}
                title="Close"
              >
                ×
              </button>
            </div>

            {/* Chunk text content */}
            <div style={{ flex: 1, padding: "12px 16px", overflowY: "auto" }}>
              {sourcePanel.loading && (
                <div style={{ fontSize: 11, color: withGlow(palette.amber, 0.6), fontFamily: "'IBM Plex Mono', monospace" }}>
                  Loading source text...
                </div>
              )}
              {sourcePanel.error && (
                <div style={{ fontSize: 11, color: semantic.error, fontFamily: "'IBM Plex Mono', monospace" }}>
                  {sourcePanel.error}
                </div>
              )}
              {sourcePanel.chunkText && (
                <div style={{
                  fontSize: 12, color: text.secondary, lineHeight: 1.7,
                  whiteSpace: "pre-wrap",
                }}>
                  {sourcePanel.chunkText}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* RHS: Graph + Explainability panel */}
      <div style={{ width: "45%", display: "flex", flexDirection: "column" }}>
        {/* Graph view — top half */}
        <div style={{ height: "45%", borderBottom: `1px solid ${border.default}`, position: "relative" }}>
          <ExplainGraph
            nodes={graphNodes}
            edges={graphEdges}
            highlightedNodeIds={highlightedNodeIds}
            highlightedEdgeIds={highlightedEdgeIds}
            onNodeClick={(nodeId) => {
              setHighlightedNodeIds(prev =>
                prev.includes(nodeId) ? prev.filter(id => id !== nodeId) : [...prev, nodeId]
              );
            }}
            onEdgeClick={(edgeId) => {
              setHighlightedEdgeIds(prev =>
                prev.includes(edgeId) ? prev.filter(id => id !== edgeId) : [...prev, edgeId]
              );
            }}
          />
        </div>

        {/* Event cards — bottom half */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0 }}>
          <div style={{ padding: "12px 20px", borderBottom: `1px solid ${border.default}` }}>
            <SectionLabel>
              EVENTS
              {explainNodes.length > 0 && (
                <span style={{ color: text.muted, fontWeight: 400, marginLeft: 8 }}>
                  {explainNodes.length} event{explainNodes.length !== 1 ? "s" : ""}
                </span>
              )}
            </SectionLabel>
          </div>

          <div style={{ flex: 1, padding: "12px 16px", overflowY: "auto" }}>
            {explainNodes.length === 0 && !isQuerying && (
              <div style={{ color: text.hint, fontSize: 13, fontStyle: "italic" }}>
                Explain events will appear here as the query progresses.
              </div>
            )}

            {isQuerying && explainNodes.length === 0 && (
              <div style={{ padding: "8px 12px", fontSize: 11, color: withGlow(palette.cyan, 0.6), fontFamily: "'IBM Plex Mono', monospace" }}>
                Waiting for explain events...
              </div>
            )}

            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {explainNodes.map((node, idx) => (
                <ExplainCard
                  key={node.explainId}
                  node={node}
                  index={idx}
                  onEntityClick={handleEntityClick}
                  onEdgeClick={handleEdgeClick}
                  onSourceClick={handleSourceClick}
                />
              ))}
            </div>
            <div ref={explainScrollRef} />
          </div>
        </div>
      </div>
    </div>
  );
}

// ── ExplainCard ─────────────────────────────────────────────────────

function ExplainCard({ node, index, onEntityClick, onEdgeClick, onSourceClick }: {
  node: ExplainNode;
  index: number;
  onEntityClick?: (uri: string) => void;
  onEdgeClick?: (sel: EdgeSelection) => void;
  onSourceClick?: (source: ProvenanceChain) => void;
}) {
  const typeColor = eventTypeColor(node.eventType);

  return (
    <div style={{
      padding: "12px 16px", borderRadius: 8,
      background: withGlow(typeColor, 0.06),
      border: `1px solid ${withGlow(typeColor, 0.15)}`,
    }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
        <span style={{
          display: "inline-block", width: 20, height: 20, borderRadius: "50%",
          background: withGlow(typeColor, 0.2), border: `1px solid ${withGlow(typeColor, 0.4)}`,
          textAlign: "center", lineHeight: "20px", fontSize: 10, color: typeColor, fontWeight: 700,
        }}>
          {index + 1}
        </span>
        <span style={{
          fontSize: 11, fontFamily: "'IBM Plex Mono', monospace",
          color: typeColor, fontWeight: 600, textTransform: "uppercase",
        }}>
          {node.eventType}
        </span>
        {node.fetching && (
          <span style={{ fontSize: 10, color: text.faint, fontStyle: "italic" }}>loading...</span>
        )}
      </div>

      {/* Event data */}
      {node.fetched && node.data && (
        <EventDataView
          eventType={node.eventType}
          data={node.data}
          onEntityClick={onEntityClick}
          onEdgeClick={onEdgeClick}
          onSourceClick={onSourceClick}
        />
      )}

      {node.error && (
        <div style={{ fontSize: 10, color: semantic.error, marginTop: 4 }}>{node.error}</div>
      )}
    </div>
  );
}

// ── EventDataView ───────────────────────────────────────────────────

function EventDataView({ eventType, data, onEntityClick, onEdgeClick, onSourceClick }: {
  eventType: string;
  data: EventData;
  onEntityClick?: (uri: string) => void;
  onEdgeClick?: (sel: EdgeSelection) => void;
  onSourceClick?: (source: ProvenanceChain) => void;
}) {
  const mono = { fontFamily: "'IBM Plex Mono', monospace" } as const;

  switch (eventType) {
    case "question": {
      const d = data as QuestionData;
      return (
        <div style={{ marginTop: 4 }}>
          {d.query && (
            <div style={{ fontSize: 12, color: text.secondary, lineHeight: 1.6, ...mono }}>
              <span style={{ color: palette.amber }}>Query:</span> {d.query}
            </div>
          )}
          {d.timestamp && (
            <div style={{ fontSize: 10, color: text.faint, marginTop: 4, ...mono }}>
              {d.timestamp}
            </div>
          )}
        </div>
      );
    }

    case "grounding": {
      const d = data as GroundingData;
      return (
        <div style={{ marginTop: 4 }}>
          {d.concepts.length > 0 && (
            <>
              <div style={{ fontSize: 11, color: palette.orange, marginBottom: 4, ...mono }}>
                {d.concepts.length} concept{d.concepts.length !== 1 ? "s" : ""} extracted
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                {d.concepts.map((concept, i) => (
                  <span key={i} style={{
                    fontSize: 11, padding: "3px 8px", borderRadius: 4,
                    background: withGlow(palette.orange, 0.1),
                    border: `1px solid ${withGlow(palette.orange, 0.2)}`,
                    color: text.secondary, ...mono,
                  }}>
                    {concept}
                  </span>
                ))}
              </div>
            </>
          )}
        </div>
      );
    }

    case "exploration": {
      const d = data as ExplorationData;
      return (
        <div style={{ marginTop: 4 }}>
          {d.edgeCount && (
            <div style={{ fontSize: 12, color: text.secondary, ...mono }}>
              <span style={{ color: palette.blue }}>Subgraph extracted:</span> {d.edgeCount} edges
            </div>
          )}
          {d.chunkCount && (
            <div style={{ fontSize: 12, color: text.secondary, ...mono }}>
              <span style={{ color: palette.blue }}>Chunks retrieved:</span> {d.chunkCount}
            </div>
          )}
          {d.entityLabels && d.entityLabels.length > 0 && (
            <div style={{ marginTop: 6 }}>
              <div style={{ fontSize: 11, color: palette.blue, marginBottom: 4, ...mono }}>
                {d.entityLabels.length} seed entit{d.entityLabels.length !== 1 ? "ies" : "y"}
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                {d.entityLabels.map((label, i) => (
                  <span
                    key={i}
                    onClick={() => onEntityClick?.(d.entities[i])}
                    style={{
                      fontSize: 11, padding: "3px 8px", borderRadius: 4,
                      background: withGlow(palette.blue, 0.1),
                      border: `1px solid ${withGlow(palette.blue, 0.2)}`,
                      color: text.secondary, ...mono,
                      cursor: onEntityClick ? "pointer" : "default",
                      transition: "all 0.15s ease",
                    }}
                    onMouseEnter={e => { if (onEntityClick) (e.currentTarget.style.background = withGlow(palette.blue, 0.25)); }}
                    onMouseLeave={e => { (e.currentTarget.style.background = withGlow(palette.blue, 0.1)); }}
                  >
                    {label}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      );
    }

    case "focus": {
      const d = data as FocusData;
      return (
        <div style={{ marginTop: 4 }}>
          {d.edgeSelections && d.edgeSelections.length > 0 && (
            <>
              <div style={{ fontSize: 11, color: palette.purple, marginBottom: 6, ...mono }}>
                Focused on {d.edgeSelections.length} edge{d.edgeSelections.length !== 1 ? "s" : ""}
              </div>
              {d.edgeSelections.map((sel, i) => (
                <EdgeSelectionView key={sel.edgeUri || i} sel={sel} onClick={() => onEdgeClick?.(sel)} onSourceClick={onSourceClick} />
              ))}
            </>
          )}
        </div>
      );
    }

    case "synthesis": {
      const d = data as SynthesisData;
      return (
        <div style={{ marginTop: 4 }}>
          {d.contentLength != null && (
            <div style={{ fontSize: 12, color: text.secondary, ...mono }}>
              <span style={{ color: palette.emerald }}>Synthesis:</span> {d.contentLength} chars
            </div>
          )}
        </div>
      );
    }

    case "analysis": {
      const d = data as AnalysisData;
      let parsedArgs: Record<string, string> | null = null;
      if (d.arguments) {
        try { parsedArgs = JSON.parse(d.arguments); } catch { /* ignore */ }
      }
      return (
        <div style={{ marginTop: 4 }}>
          {d.action && (
            <div style={{ fontSize: 12, color: text.secondary, ...mono, marginBottom: 4 }}>
              <span style={{ color: palette.purple }}>Tool:</span> {d.action}
            </div>
          )}
          {parsedArgs && Object.entries(parsedArgs).map(([key, val]) => (
            <div key={key} style={{ fontSize: 11, color: text.muted, lineHeight: 1.5, ...mono }}>
              <span style={{ color: text.subtle }}>{key}:</span> {String(val)}
            </div>
          ))}
          {!parsedArgs && d.arguments && (
            <div style={{ fontSize: 11, color: text.muted, ...mono }}>
              {d.arguments}
            </div>
          )}
        </div>
      );
    }

    case "conclusion": {
      const d = data as ConclusionData;
      return (
        <div style={{ marginTop: 4 }}>
          {d.documentUri && (
            <div style={{ fontSize: 11, color: text.muted, ...mono }}>
              {shortUri(d.documentUri)}
            </div>
          )}
        </div>
      );
    }

    case "reflection": {
      const d = data as ReflectionData;
      return (
        <div style={{ marginTop: 4 }}>
          {d.documentUri && (
            <div style={{ fontSize: 11, color: text.muted, ...mono }}>
              {shortUri(d.documentUri)}
            </div>
          )}
        </div>
      );
    }

    default:
      return null;
  }
}

// ── EdgeSelectionView ───────────────────────────────────────────────

function EdgeSelectionView({ sel, onClick, onSourceClick }: {
  sel: EdgeSelection;
  onClick?: () => void;
  onSourceClick?: (source: ProvenanceChain) => void;
}) {
  const mono = { fontFamily: "'IBM Plex Mono', monospace" } as const;

  return (
    <div
      onClick={onClick}
      style={{
        padding: "6px 10px", marginBottom: 4, borderRadius: 6,
        borderLeft: `3px solid ${withGlow(palette.purple, 0.3)}`,
        cursor: onClick ? "pointer" : "default",
        transition: "background 0.15s ease",
      }}
      onMouseEnter={e => { if (onClick) e.currentTarget.style.background = withGlow(palette.purple, 0.08); }}
      onMouseLeave={e => { e.currentTarget.style.background = "transparent"; }}
    >
      {/* Edge triple */}
      {sel.edgeLabels && (
        <div style={{ fontSize: 11, lineHeight: 1.5, ...mono }}>
          <span style={{ color: palette.pink }}>{sel.edgeLabels.s}</span>
          <span style={{ color: text.faint }}> → </span>
          <span style={{ color: palette.cyan }}>{sel.edgeLabels.p}</span>
          <span style={{ color: text.faint }}> → </span>
          <span style={{ color: palette.pink }}>{sel.edgeLabels.o}</span>
        </div>
      )}

      {/* Provenance sources — clickable to view source text */}
      {sel.sources && sel.sources.length > 0 && (
        <div style={{ marginTop: 3, display: "flex", flexWrap: "wrap", gap: 4 }}>
          {sel.sources.map((source, si) => {
            const chainLabel = source.chain.map(c => c.label).join(" → ");
            return (
              <span
                key={si}
                onClick={(e) => {
                  e.stopPropagation();
                  onSourceClick?.(source);
                }}
                title={`View source: ${chainLabel}`}
                style={{
                  fontSize: 10, padding: "2px 7px", borderRadius: 4,
                  background: withGlow(palette.amber, 0.08),
                  border: `1px solid ${withGlow(palette.amber, 0.2)}`,
                  color: text.hint, ...mono,
                  cursor: onSourceClick ? "pointer" : "default",
                  transition: "all 0.15s ease",
                }}
                onMouseEnter={e => { if (onSourceClick) { e.currentTarget.style.background = withGlow(palette.amber, 0.2); e.currentTarget.style.color = palette.amber; } }}
                onMouseLeave={e => { e.currentTarget.style.background = withGlow(palette.amber, 0.08); e.currentTarget.style.color = text.hint; }}
              >
                {chainLabel}
              </span>
            );
          })}
        </div>
      )}

      {/* Reasoning - compact */}
      {sel.reasoning && (
        <div style={{ fontSize: 10, color: text.subtle, lineHeight: 1.4, fontStyle: "italic", marginTop: 2 }}>
          {sel.reasoning.length > 120 ? sel.reasoning.slice(0, 120) + "..." : sel.reasoning}
        </div>
      )}
    </div>
  );
}
