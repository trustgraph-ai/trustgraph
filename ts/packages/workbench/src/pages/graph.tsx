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
  Filter,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useSocket } from "@/providers/socket-provider";
import { useSessionStore } from "@/hooks/use-session-store";
import { useSettings } from "@/providers/settings-provider";
import { useProgressStore } from "@/hooks/use-progress-store";
import { Badge } from "@/components/ui/badge";
import type { Triple, Term } from "@trustgraph/client";
import {
  termValue,
  localName,
  hashColor,
  triplesToGraph,
  RDFS_LABEL,
  RDF_TYPE,
  type GraphNode,
  type GraphLink,
} from "@/lib/graph-utils";

// ---------------------------------------------------------------------------
// Lazy-load ForceGraph2D to keep bundle size down
// ---------------------------------------------------------------------------

import type {
  ForceGraphMethods,
  ForceGraphProps,
} from "react-force-graph-2d";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const ForceGraph2D = lazy(() => import("react-force-graph-2d")) as unknown as React.ComponentType<ForceGraphProps<any, any> & { ref?: React.Ref<any> }>;

// Graph helpers imported from @/lib/graph-utils

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

  // Query filters
  const [showFilters, setShowFilters] = useState(false);
  const [subjectFilter, setSubjectFilter] = useState("");
  const [predicateFilter, setPredicateFilter] = useState("");
  const [objectFilter, setObjectFilter] = useState("");
  const [tripleLimit, setTripleLimit] = useState(2000);
  const [showLegend, setShowLegend] = useState(false);
  const hasActiveFilters = subjectFilter || predicateFilter || objectFilter;

  const fgRef = useRef<ForceGraphMethods<GraphNode, GraphLink> | undefined>(
    undefined,
  );
  const [containerSize, setContainerSize] = useState<{
    width: number;
    height: number;
  } | null>(null);
  const roRef = useRef<ResizeObserver | null>(null);

  // Auto-fit tracking — declared early so fetchTriples can reset it
  const hasAutoFit = useRef(false);

  // Ref callback — attaches ResizeObserver when the container mounts
  const containerRef = useCallback((el: HTMLDivElement | null) => {
    // Disconnect previous observer
    if (roRef.current) {
      roRef.current.disconnect();
      roRef.current = null;
    }
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        const { width, height } = entry.contentRect;
        setContainerSize({ width: Math.floor(width), height: Math.floor(height) });
      }
    });
    ro.observe(el);
    roRef.current = ro;
  }, []);

  // Fetch triples with optional filters
  const fetchTriples = useCallback(async () => {
    const act = "Load graph";
    try {
      setLoading(true);
      setError(null);
      addActivity(act);
      hasAutoFit.current = false;

      const flow = socket.flow(flowId);
      const s: Term | undefined = subjectFilter ? { t: "i", i: subjectFilter } : undefined;
      const p: Term | undefined = predicateFilter ? { t: "i", i: predicateFilter } : undefined;
      const o: Term | undefined = objectFilter ? { t: "i", i: objectFilter } : undefined;

      const result = await flow.triplesQuery(
        s,
        p,
        o,
        tripleLimit,
        collection,
      );
      setTriples(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
      removeActivity(act);
    }
  }, [socket, flowId, collection, subjectFilter, predicateFilter, objectFilter, tripleLimit, addActivity, removeActivity]);

  useEffect(() => {
    fetchTriples();
  }, [fetchTriples]);

  // Build graph
  const { data: graphData, labelMap, typeMap } = useMemo(
    () => triplesToGraph(Array.isArray(triples) ? triples : []),
    [triples],
  );

  // Unique types for legend
  const uniqueTypes = useMemo(() => {
    const seen = new Map<string, string>();
    for (const [, typeUri] of typeMap) {
      const name = localName(typeUri);
      if (!seen.has(name)) {
        seen.set(name, typeUri);
      }
    }
    return Array.from(seen.entries());
  }, [typeMap]);

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

  // Auto-fit graph to view once data loads
  useEffect(() => {
    if (graphData.nodes.length > 0 && fgRef.current && !hasAutoFit.current) {
      hasAutoFit.current = true;
      // Wait for force simulation to settle briefly before fitting
      const timer = setTimeout(() => fgRef.current?.zoomToFit(400, 40), 500);
      return () => clearTimeout(timer);
    }
  }, [graphData.nodes.length]);

  // Zoom helpers
  const zoomIn = () => fgRef.current?.zoom(2, 300);
  const zoomOut = () => fgRef.current?.zoom(0.5, 300);
  const zoomFit = () =>
    fgRef.current?.zoomToFit(400, 40);

  // Node paint callback — with glow effect
  const paintNode = useCallback(
    (node: GraphNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const isSelected = node.id === selectedNode;
      const isMatch = matchingIds.size > 0 && matchingIds.has(node.id);
      const dim = matchingIds.size > 0 && !isMatch && !isSelected;

      const radius = Math.max(3, Math.sqrt(node.degree + 1) * 2.5);
      const x = node.x ?? 0;
      const y = node.y ?? 0;

      const baseColor = dim
        ? "rgba(100,100,100,0.3)"
        : isSelected
          ? "#fbbf24"
          : isMatch
            ? "#22c55e"
            : node.color ?? "#5b80ff";

      // Outer glow (only when not dimmed)
      if (!dim) {
        ctx.save();
        ctx.shadowColor = baseColor;
        ctx.shadowBlur = isSelected ? 16 : 8;
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, 2 * Math.PI);
        ctx.fillStyle = baseColor;
        ctx.fill();
        ctx.restore();
      }

      // Node circle (crisp, on top of glow)
      ctx.beginPath();
      ctx.arc(x, y, radius, 0, 2 * Math.PI);
      ctx.fillStyle = baseColor;
      ctx.fill();

      // Inner highlight (subtle white dot for depth)
      if (!dim && radius > 3) {
        ctx.beginPath();
        ctx.arc(x - radius * 0.25, y - radius * 0.25, radius * 0.3, 0, 2 * Math.PI);
        ctx.fillStyle = "rgba(255,255,255,0.2)";
        ctx.fill();
      }

      if (isSelected || isMatch) {
        ctx.strokeStyle = isSelected ? "#fbbf24" : "#22c55e";
        ctx.lineWidth = 1.5 / globalScale;
        ctx.stroke();
      }

      // Label
      const fontSize = Math.max(10 / globalScale, 2);
      ctx.font = `600 ${fontSize}px Inter, sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      const isLight = document.documentElement.classList.contains("light");
      ctx.fillStyle = dim
        ? "rgba(100,100,100,0.3)"
        : isLight
          ? "rgba(24,24,27,0.9)"
          : "rgba(250,250,250,0.9)";
      ctx.fillText(node.label, x, y + radius + 2);
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
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <Rotate3d className="h-6 w-6 text-brand-400" />
          <h1 className="text-2xl font-bold text-fg">Graph</h1>
          <span className="ml-2 rounded bg-surface-200 px-2 py-0.5 text-xs text-fg-muted">
            {graphData.nodes.length} nodes, {graphData.links.length} edges
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-fg-subtle" />
            <input
              id="graph-search"
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search nodes..."
              aria-label="Search nodes"
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

          {/* Filter toggle */}
          <button
            onClick={() => setShowFilters((p) => !p)}
            className={cn(
              "flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs transition-colors",
              showFilters || hasActiveFilters
                ? "border-brand-500/50 bg-brand-600/10 text-brand-400"
                : "border-border text-fg-muted hover:bg-surface-200",
            )}
            title="Query filters"
            aria-label="Toggle query filters"
            aria-expanded={showFilters}
          >
            <Filter className="h-3.5 w-3.5" />
            Filters
            {hasActiveFilters && !showFilters && (
              <span className="ml-0.5 h-1.5 w-1.5 rounded-full bg-brand-400" />
            )}
          </button>

          {/* Legend toggle */}
          {uniqueTypes.length > 0 && (
            <button
              onClick={() => setShowLegend((p) => !p)}
              className={cn(
                "flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs transition-colors",
                showLegend
                  ? "border-brand-500/50 bg-brand-600/10 text-brand-400"
                  : "border-border text-fg-muted hover:bg-surface-200",
              )}
              title="Type legend"
              aria-label="Toggle type legend"
              aria-expanded={showLegend}
            >
              Legend
            </button>
          )}

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

      {/* Filter panel */}
      {showFilters && (
        <div className="mb-4 rounded-lg border border-border bg-surface-50 p-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="flex items-center gap-2 text-xs font-medium text-fg-muted">
              <Filter className="h-3 w-3" />
              Query Filters
            </h3>
            {hasActiveFilters && (
              <button
                onClick={() => {
                  setSubjectFilter("");
                  setPredicateFilter("");
                  setObjectFilter("");
                }}
                className="text-xs text-brand-400 hover:text-brand-300"
              >
                Clear all
              </button>
            )}
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div className="space-y-1">
              <label htmlFor="filter-subject" className="block text-[10px] font-medium uppercase tracking-wider text-fg-subtle">
                Subject
              </label>
              <input
                id="filter-subject"
                type="text"
                value={subjectFilter}
                onChange={(e) => setSubjectFilter(e.target.value)}
                placeholder="URI filter..."
                className="w-full rounded-lg border border-border bg-surface-100 px-3 py-1.5 text-xs text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            </div>
            <div className="space-y-1">
              <label htmlFor="filter-predicate" className="block text-[10px] font-medium uppercase tracking-wider text-fg-subtle">
                Predicate
              </label>
              <input
                id="filter-predicate"
                type="text"
                value={predicateFilter}
                onChange={(e) => setPredicateFilter(e.target.value)}
                placeholder="URI filter..."
                className="w-full rounded-lg border border-border bg-surface-100 px-3 py-1.5 text-xs text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            </div>
            <div className="space-y-1">
              <label htmlFor="filter-object" className="block text-[10px] font-medium uppercase tracking-wider text-fg-subtle">
                Object
              </label>
              <input
                id="filter-object"
                type="text"
                value={objectFilter}
                onChange={(e) => setObjectFilter(e.target.value)}
                placeholder="URI filter..."
                className="w-full rounded-lg border border-border bg-surface-100 px-3 py-1.5 text-xs text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            </div>
          </div>
          <div className="mt-3 flex items-center gap-4">
            <div className="flex items-center gap-2">
              <label htmlFor="filter-limit" className="text-[10px] font-medium uppercase tracking-wider text-fg-subtle">
                Limit
              </label>
              <input
                id="filter-limit"
                type="range"
                min={100}
                max={5000}
                step={100}
                value={tripleLimit}
                onChange={(e) => setTripleLimit(Number(e.target.value))}
                className="w-24 accent-brand-500"
              />
              <span className="text-xs text-fg-muted">{tripleLimit}</span>
            </div>
            <button
              onClick={fetchTriples}
              disabled={loading}
              className="ml-auto flex items-center gap-1.5 rounded-lg bg-brand-600 px-4 py-1.5 text-xs font-medium text-white transition-colors hover:bg-brand-500 disabled:opacity-40"
            >
              Apply
            </button>
          </div>
        </div>
      )}

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
        <div className="relative flex flex-1 overflow-hidden rounded-lg border border-border">
          {/* Graph canvas */}
          <div ref={containerRef} className="relative min-w-0 flex-1 bg-surface-0">
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
              linkColor={() => "rgba(91,128,255,0.18)"}
              linkWidth={1.5}
              linkDirectionalArrowLength={5}
              linkDirectionalArrowRelPos={0.85}
              linkDirectionalArrowColor={() => "rgba(91,128,255,0.5)"}
              linkDirectionalParticles={2}
              linkDirectionalParticleWidth={2}
              linkDirectionalParticleSpeed={0.004}
              linkDirectionalParticleColor={() => "rgba(91,128,255,0.6)"}
              linkCurvature={0.1}
              onNodeClick={(node: GraphNode) => {
                setSelectedNode((prev) =>
                  prev === node.id ? null : node.id,
                );
              }}
              onBackgroundClick={() => setSelectedNode(null)}
              backgroundColor="transparent"
              cooldownTicks={100}
              warmupTicks={30}
              width={containerSize?.width}
              height={containerSize?.height}
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

          {/* Type legend overlay */}
          {showLegend && uniqueTypes.length > 0 && (
            <div className="absolute bottom-3 left-3 z-10 max-h-48 overflow-y-auto rounded-lg border border-border bg-surface-50/95 px-3 py-2 shadow-lg backdrop-blur-sm">
              <h4 className="mb-1.5 text-[10px] font-medium uppercase tracking-wider text-fg-subtle">
                Node Types
              </h4>
              <div className="space-y-1">
                {uniqueTypes.map(([name]) => (
                  <div key={name} className="flex items-center gap-2 text-xs text-fg-muted">
                    <span
                      className="inline-block h-2.5 w-2.5 shrink-0 rounded-full"
                      style={{ backgroundColor: hashColor(name) }}
                    />
                    <span className="truncate">{name}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Detail panel -- positioned absolutely so it overlays the graph */}
          {selectedNode && (
            <div className="absolute inset-y-0 right-0 z-10">
              <NodeDetailPanel
                nodeId={selectedNode}
                label={selectedLabel}
                triples={triples}
                labelMap={labelMap}
                onClose={() => setSelectedNode(null)}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
