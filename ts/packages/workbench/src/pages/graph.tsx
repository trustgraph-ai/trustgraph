import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  Rotate3d,
  Search,
  ZoomIn,
  ZoomOut,
  Maximize,
  Loader2,
  X,
  ArrowRight,
  ArrowLeft,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useSocket } from "@/providers/socket-provider";
import { useSessionStore } from "@/hooks/use-session-store";
import { useSettings } from "@/providers/settings-provider";
import { useProgressStore } from "@/hooks/use-progress-store";
import { Badge } from "@/components/ui/badge";
import type { Triple, Term } from "@trustgraph/client";

// ---------------------------------------------------------------------------
// Lazy-load ForceGraph2D to keep bundle size down
// ---------------------------------------------------------------------------

import type {
  ForceGraphMethods,
  NodeObject,
  LinkObject,
  ForceGraphProps,
} from "react-force-graph-2d";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const ForceGraph2D = lazy(() => import("react-force-graph-2d")) as unknown as React.ComponentType<ForceGraphProps<any, any> & { ref?: React.Ref<any> }>;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface GraphNode extends NodeObject {
  id: string;
  label: string;
  color?: string;
  /** Number of connections (used for sizing) */
  degree: number;
}

interface GraphLink extends LinkObject {
  source: string;
  target: string;
  label: string;
}

interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

// ---------------------------------------------------------------------------
// Helpers -- Term value extraction
// ---------------------------------------------------------------------------

const RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label";
const RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type";

function termValue(t: Term): string {
  switch (t.t) {
    case "i":
      return t.i;
    case "l":
      return t.v;
    case "b":
      return t.d;
    case "t":
      return "[triple]";
  }
}

function isIri(t: Term): boolean {
  return t.t === "i";
}

/** Extract the local name from a URI for display */
function localName(uri: string): string {
  const hash = uri.lastIndexOf("#");
  const slash = uri.lastIndexOf("/");
  const idx = Math.max(hash, slash);
  if (idx >= 0 && idx < uri.length - 1) return uri.substring(idx + 1);
  return uri;
}

/** Deterministic color from a string (for node types) */
function hashColor(s: string): string {
  let hash = 0;
  for (let i = 0; i < s.length; i++) {
    hash = s.charCodeAt(i) + ((hash << 5) - hash);
  }
  const hue = ((hash % 360) + 360) % 360;
  return `hsl(${hue}, 60%, 55%)`;
}

// ---------------------------------------------------------------------------
// Build graph data from triples
// ---------------------------------------------------------------------------

function triplesToGraph(triples: Triple[]): {
  data: GraphData;
  labelMap: Map<string, string>;
  typeMap: Map<string, string>;
} {
  const labelMap = new Map<string, string>();
  const typeMap = new Map<string, string>();

  // First pass: collect labels and types
  for (const t of triples) {
    const pred = termValue(t.p);
    if (pred === RDFS_LABEL && t.o.t === "l") {
      labelMap.set(termValue(t.s), t.o.v);
    }
    if (pred === RDF_TYPE && isIri(t.o)) {
      typeMap.set(termValue(t.s), termValue(t.o));
    }
  }

  // Second pass: build nodes and links (skip structural triples)
  const nodeMap = new Map<string, GraphNode>();
  const links: GraphLink[] = [];

  const ensureNode = (uri: string): void => {
    if (!nodeMap.has(uri)) {
      const type = typeMap.get(uri);
      nodeMap.set(uri, {
        id: uri,
        label: labelMap.get(uri) ?? localName(uri),
        color: type ? hashColor(localName(type)) : "#5b80ff",
        degree: 0,
      });
    }
  };

  for (const t of triples) {
    const sVal = termValue(t.s);
    const pVal = termValue(t.p);
    const oVal = termValue(t.o);

    // Skip label and type predicates -- they are metadata, not graph edges
    if (pVal === RDFS_LABEL) continue;
    if (pVal === RDF_TYPE) continue;

    // Build edges for entity-to-entity relationships.
    // Include both IRIs and literals as valid entity nodes — plain-name
    // knowledge graphs (e.g. seeded demo data) use literals for entities.
    const sIsEntity = isIri(t.s) || t.s.t === "l";
    const oIsEntity = isIri(t.o) || t.o.t === "l";
    if (!sIsEntity || !oIsEntity) continue;

    ensureNode(sVal);
    ensureNode(oVal);
    nodeMap.get(sVal)!.degree++;
    nodeMap.get(oVal)!.degree++;

    links.push({
      source: sVal,
      target: oVal,
      label: labelMap.get(pVal) ?? localName(pVal),
    });
  }

  return {
    data: { nodes: Array.from(nodeMap.values()), links },
    labelMap,
    typeMap,
  };
}

// ---------------------------------------------------------------------------
// Node detail panel
// ---------------------------------------------------------------------------

function NodeDetailPanel({
  nodeId,
  label,
  triples,
  labelMap,
  onClose,
}: {
  nodeId: string;
  label: string;
  triples: Triple[];
  labelMap: Map<string, string>;
  onClose: () => void;
}) {
  // Find triples where this node is subject or object
  const related = useMemo(() => {
    const outbound: { predicate: string; object: string; objectLabel: string }[] = [];
    const inbound: { predicate: string; subject: string; subjectLabel: string }[] = [];

    for (const t of triples) {
      const sVal = termValue(t.s);
      const pVal = termValue(t.p);
      const oVal = termValue(t.o);

      if (pVal === RDFS_LABEL || pVal === RDF_TYPE) continue;

      if (sVal === nodeId) {
        outbound.push({
          predicate: labelMap.get(pVal) ?? localName(pVal),
          object: oVal,
          objectLabel: labelMap.get(oVal) ?? localName(oVal),
        });
      }
      if (oVal === nodeId) {
        inbound.push({
          predicate: labelMap.get(pVal) ?? localName(pVal),
          subject: sVal,
          subjectLabel: labelMap.get(sVal) ?? localName(sVal),
        });
      }
    }
    return { outbound, inbound };
  }, [nodeId, triples, labelMap]);

  return (
    <div className="flex h-full w-80 shrink-0 flex-col border-l border-border bg-surface-50">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h3 className="truncate text-sm font-semibold text-fg">{label}</h3>
        <button
          onClick={onClose}
          className="rounded p-1 text-fg-subtle hover:bg-surface-200 hover:text-fg"
          aria-label="Close detail panel"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <p className="mb-3 truncate font-mono text-[10px] text-fg-subtle">
          {nodeId}
        </p>

        {/* Outbound relationships */}
        {related.outbound.length > 0 && (
          <div className="mb-4">
            <h4 className="mb-2 flex items-center gap-1.5 text-xs font-medium text-fg-muted">
              <ArrowRight className="h-3 w-3" />
              Outbound ({related.outbound.length})
            </h4>
            <div className="space-y-1">
              {related.outbound.map((r, i) => (
                <div
                  key={i}
                  className="flex items-center gap-1.5 rounded bg-surface-100 px-2 py-1.5 text-xs"
                >
                  <Badge variant="default">{r.predicate}</Badge>
                  <span className="truncate text-fg-muted">{r.objectLabel}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Inbound relationships */}
        {related.inbound.length > 0 && (
          <div>
            <h4 className="mb-2 flex items-center gap-1.5 text-xs font-medium text-fg-muted">
              <ArrowLeft className="h-3 w-3" />
              Inbound ({related.inbound.length})
            </h4>
            <div className="space-y-1">
              {related.inbound.map((r, i) => (
                <div
                  key={i}
                  className="flex items-center gap-1.5 rounded bg-surface-100 px-2 py-1.5 text-xs"
                >
                  <span className="truncate text-fg-muted">{r.subjectLabel}</span>
                  <Badge variant="default">{r.predicate}</Badge>
                </div>
              ))}
            </div>
          </div>
        )}

        {related.outbound.length === 0 && related.inbound.length === 0 && (
          <p className="text-xs text-fg-subtle">No relationships found.</p>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Graph page
// ---------------------------------------------------------------------------

export default function GraphPage() {
  const socket = useSocket();
  const flowId = useSessionStore((s) => s.flowId);
  const collection = useSettings((s) => s.settings.collection);
  const addActivity = useProgressStore((s) => s.addActivity);
  const removeActivity = useProgressStore((s) => s.removeActivity);

  const [triples, setTriples] = useState<Triple[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  const fgRef = useRef<ForceGraphMethods<GraphNode, GraphLink> | undefined>(
    undefined,
  );

  // Fetch triples
  const fetchTriples = useCallback(async () => {
    const act = "Load graph";
    try {
      setLoading(true);
      setError(null);
      addActivity(act);

      const flow = socket.flow(flowId);
      const result = await flow.triplesQuery(
        undefined,
        undefined,
        undefined,
        2000,
        collection,
      );
      setTriples(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
      removeActivity(act);
    }
  }, [socket, flowId, collection, addActivity, removeActivity]);

  useEffect(() => {
    fetchTriples();
  }, [fetchTriples]);

  // Build graph
  const { data: graphData, labelMap } = useMemo(
    () => triplesToGraph(Array.isArray(triples) ? triples : []),
    [triples],
  );

  // Search filter -- highlight matching nodes
  const searchLower = searchTerm.toLowerCase();
  const matchingIds = useMemo(() => {
    if (!searchLower) return new Set<string>();
    return new Set(
      graphData.nodes
        .filter(
          (n) =>
            n.label.toLowerCase().includes(searchLower) ||
            n.id.toLowerCase().includes(searchLower),
        )
        .map((n) => n.id),
    );
  }, [graphData.nodes, searchLower]);

  const selectedLabel = selectedNode
    ? labelMap.get(selectedNode) ?? localName(selectedNode)
    : "";

  // Zoom helpers
  const zoomIn = () => fgRef.current?.zoom(2, 300);
  const zoomOut = () => fgRef.current?.zoom(0.5, 300);
  const zoomFit = () =>
    fgRef.current?.zoomToFit(400, 40);

  // Node paint callback
  const paintNode = useCallback(
    (node: GraphNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const isSelected = node.id === selectedNode;
      const isMatch = matchingIds.size > 0 && matchingIds.has(node.id);
      const dim = matchingIds.size > 0 && !isMatch && !isSelected;

      const radius = Math.max(3, Math.sqrt(node.degree + 1) * 2.5);
      const x = node.x ?? 0;
      const y = node.y ?? 0;

      // Node circle
      ctx.beginPath();
      ctx.arc(x, y, radius, 0, 2 * Math.PI);
      ctx.fillStyle = dim
        ? "rgba(100,100,100,0.3)"
        : isSelected
          ? "#fbbf24"
          : isMatch
            ? "#22c55e"
            : node.color ?? "#5b80ff";
      ctx.fill();

      if (isSelected || isMatch) {
        ctx.strokeStyle = isSelected ? "#fbbf24" : "#22c55e";
        ctx.lineWidth = 1.5 / globalScale;
        ctx.stroke();
      }

      // Label
      const fontSize = Math.max(10 / globalScale, 2);
      ctx.font = `${fontSize}px Inter, sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      const isLight = document.documentElement.classList.contains("light");
      ctx.fillStyle = dim
        ? "rgba(100,100,100,0.3)"
        : isLight
          ? "rgba(24,24,27,0.9)"
          : "rgba(250,250,250,0.9)";
      ctx.fillText(node.label, x, y + radius + 1);
    },
    [selectedNode, matchingIds],
  );

  // Link label painting
  const paintLink = useCallback(
    (link: GraphLink, ctx: CanvasRenderingContext2D, globalScale: number) => {
      if (globalScale < 1.5) return; // only show labels when zoomed in enough

      const src = link.source as unknown as GraphNode;
      const tgt = link.target as unknown as GraphNode;
      if (!src.x || !tgt.x) return;

      const midX = ((src.x ?? 0) + (tgt.x ?? 0)) / 2;
      const midY = ((src.y ?? 0) + (tgt.y ?? 0)) / 2;

      const fontSize = Math.max(8 / globalScale, 1.5);
      ctx.font = `${fontSize}px Inter, sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillStyle = "rgba(161,161,170,0.7)";
      ctx.fillText(link.label, midX, midY);
    },
    [],
  );

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Rotate3d className="h-6 w-6 text-brand-400" />
          <h1 className="text-2xl font-bold text-fg">Graph</h1>
          <span className="ml-2 rounded bg-surface-200 px-2 py-0.5 text-xs text-fg-subtle">
            {graphData.nodes.length} nodes, {graphData.links.length} edges
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-fg-subtle" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search nodes..."
              className="w-48 rounded-lg border border-border bg-surface-100 py-1.5 pl-8 pr-3 text-xs text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
            {searchTerm && (
              <button
                onClick={() => setSearchTerm("")}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-fg-subtle hover:text-fg"
                aria-label="Clear search"
              >
                <X className="h-3 w-3" />
              </button>
            )}
          </div>

          {/* Zoom controls */}
          <div className="flex rounded-lg border border-border bg-surface-100">
            <button
              onClick={zoomIn}
              className="px-2 py-1.5 text-fg-muted hover:text-fg"
              title="Zoom in"
              aria-label="Zoom in"
            >
              <ZoomIn className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={zoomOut}
              className="border-l border-r border-border px-2 py-1.5 text-fg-muted hover:text-fg"
              title="Zoom out"
              aria-label="Zoom out"
            >
              <ZoomOut className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={zoomFit}
              className="px-2 py-1.5 text-fg-muted hover:text-fg"
              title="Fit to view"
              aria-label="Fit to view"
            >
              <Maximize className="h-3.5 w-3.5" />
            </button>
          </div>

          <button
            onClick={fetchTriples}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs text-fg-muted hover:bg-surface-200 disabled:opacity-40"
          >
            {loading ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Rotate3d className="h-3.5 w-3.5" />
            )}
            Reload
          </button>
        </div>
      </div>

      {/* Content */}
      {error && (
        <p className="mb-4 rounded-lg bg-error/10 px-4 py-2 text-sm text-error">
          {error}
        </p>
      )}

      {loading && triples.length === 0 && (
        <div className="flex flex-1 items-center justify-center">
          <Loader2 className="mr-2 h-5 w-5 animate-spin text-fg-subtle" />
          <span className="text-fg-subtle">Loading graph data...</span>
        </div>
      )}

      {!loading && graphData.nodes.length === 0 && (
        <div className="flex flex-1 items-center justify-center rounded-lg border border-dashed border-border">
          <div className="text-center">
            <Rotate3d className="mx-auto mb-3 h-10 w-10 text-fg-subtle opacity-30" />
            <p className="text-fg-subtle">No graph data in this collection.</p>
            <p className="mt-1 text-xs text-fg-subtle">
              Upload documents and process them to populate the knowledge graph.
            </p>
          </div>
        </div>
      )}

      {graphData.nodes.length > 0 && (
        <div className="flex flex-1 overflow-hidden rounded-lg border border-border">
          {/* Graph canvas */}
          <div className="relative flex-1 bg-surface-0">
            <Suspense fallback={<div className="flex h-full items-center justify-center"><Loader2 className="h-5 w-5 animate-spin text-fg-subtle" /></div>}>
            <ForceGraph2D
              ref={fgRef}
              graphData={graphData}
              nodeCanvasObject={paintNode}
              nodePointerAreaPaint={(node: GraphNode, color, ctx) => {
                const radius = Math.max(3, Math.sqrt(node.degree + 1) * 2.5);
                ctx.beginPath();
                ctx.arc(node.x ?? 0, node.y ?? 0, radius + 2, 0, 2 * Math.PI);
                ctx.fillStyle = color;
                ctx.fill();
              }}
              linkCanvasObjectMode={() => "after"}
              linkCanvasObject={paintLink}
              linkColor={() => "rgba(91,128,255,0.25)"}
              linkDirectionalArrowLength={4}
              linkDirectionalArrowRelPos={0.85}
              onNodeClick={(node: GraphNode) => {
                setSelectedNode((prev) =>
                  prev === node.id ? null : node.id,
                );
              }}
              onBackgroundClick={() => setSelectedNode(null)}
              backgroundColor="transparent"
              width={undefined}
              height={undefined}
            />
            </Suspense>

            {/* Search results badge overlay */}
            {searchTerm && matchingIds.size > 0 && (
              <div className="absolute bottom-3 left-3">
                <Badge variant="success">
                  {matchingIds.size} match{matchingIds.size > 1 ? "es" : ""}
                </Badge>
              </div>
            )}
          </div>

          {/* Detail panel */}
          {selectedNode && (
            <NodeDetailPanel
              nodeId={selectedNode}
              label={selectedLabel}
              triples={triples}
              labelMap={labelMap}
              onClose={() => setSelectedNode(null)}
            />
          )}
        </div>
      )}
    </div>
  );
}
