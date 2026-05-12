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
  Network,
  ChevronRight,
  ChevronDown,
  Maximize,
  Loader2,
} from "lucide-react";
import { useSocket } from "@/providers/socket-provider";
import { useSessionStore } from "@/hooks/use-session-store";
import {
  triplesToGraph,
  localName,
  hashColor,
  type GraphNode,
  type GraphLink,
} from "@/lib/graph-utils";
import type { ExplainEvent, Triple } from "@trustgraph/client";
import type { ForceGraphMethods, ForceGraphProps } from "react-force-graph-2d";
import { Badge } from "@/components/ui/badge";

// ---------------------------------------------------------------------------
// Lazy-load ForceGraph2D (shares the same chunk as the graph page)
// ---------------------------------------------------------------------------

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const ForceGraph2D = lazy(() => import("react-force-graph-2d")) as unknown as React.ComponentType<ForceGraphProps<any, any> & { ref?: React.Ref<any> }>;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface ExplainGraphProps {
  explainEvents: ExplainEvent[];
  collection: string;
}

export function ExplainGraph({ explainEvents, collection }: ExplainGraphProps) {
  const socket = useSocket();
  const flowId = useSessionStore((s) => s.flowId);

  const [expanded, setExpanded] = useState(false);
  const [triples, setTriples] = useState<Triple[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fetched, setFetched] = useState(false);

  const fgRef = useRef<ForceGraphMethods<GraphNode, GraphLink> | undefined>(
    undefined,
  );
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(0);

  // Track container width for the force graph
  useEffect(() => {
    if (!expanded || containerRef.current === null) return;
    const ro = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry !== undefined) setContainerWidth(Math.floor(entry.contentRect.width));
    });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, [expanded]);

  // Load triples when first expanded — use inline triples if available, otherwise fetch
  useEffect(() => {
    if (!expanded || fetched) return;
    setFetched(true);

    // Check if any explain events have inline triples
    const inlineTriples = explainEvents.flatMap((ev) => ev.explainTriples ?? []);
    if (inlineTriples.length > 0) {
      setTriples(inlineTriples);
      return;
    }

    // Fall back to fetching from named graph
    const graphUris = explainEvents.filter(
      (ev): ev is ExplainEvent & { explainGraph: string } =>
        ev.explainGraph !== undefined && ev.explainGraph.length > 0,
    );
    if (graphUris.length === 0) return;

    setLoading(true);
    setError(null);
    const flow = socket.flow(flowId);

    Promise.all(
      graphUris.map((ev) =>
        flow
          .triplesQuery(undefined, undefined, undefined, 500, collection, ev.explainGraph)
          .catch(() => [] as Triple[]),
      ),
    )
      .then((results) => {
        setTriples(results.flat());
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        setLoading(false);
      });
  }, [expanded, fetched, explainEvents, socket, flowId, collection]);

  // Build graph data
  const { data: graphData, typeMap } = useMemo(
    () => triplesToGraph(triples),
    [triples],
  );

  // Auto-fit once data loads
  const hasAutoFit = useRef(false);
  useEffect(() => {
    if (
      graphData.nodes.length > 0 &&
      fgRef.current !== undefined &&
      hasAutoFit.current === false
    ) {
      hasAutoFit.current = true;
      const timer = setTimeout(() => fgRef.current?.zoomToFit(400, 20), 500);
      return () => clearTimeout(timer);
    }
  }, [graphData.nodes.length]);

  // Node painting (simplified version of graph page)
  const paintNode = useCallback(
    (node: GraphNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const radius = Math.max(2.5, Math.sqrt(node.degree + 1) * 2);
      const x = node.x ?? 0;
      const y = node.y ?? 0;

      ctx.beginPath();
      ctx.arc(x, y, radius, 0, 2 * Math.PI);
      ctx.fillStyle = node.color ?? "#5b80ff";
      ctx.fill();

      const fontSize = Math.max(9 / globalScale, 1.5);
      ctx.font = `${fontSize}px Inter, sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      const isLight = document.documentElement.classList.contains("light");
      ctx.fillStyle = isLight
        ? "rgba(24,24,27,0.85)"
        : "rgba(250,250,250,0.85)";
      ctx.fillText(node.label, x, y + radius + 1);
    },
    [],
  );

  // Link label painting
  const paintLink = useCallback(
    (link: GraphLink, ctx: CanvasRenderingContext2D, globalScale: number) => {
      if (globalScale < 1.5) return;
      const src = link.source as unknown as GraphNode;
      const tgt = link.target as unknown as GraphNode;
      if (
        src.x === undefined ||
        src.y === undefined ||
        tgt.x === undefined ||
        tgt.y === undefined
      ) {
        return;
      }

      const midX = ((src.x ?? 0) + (tgt.x ?? 0)) / 2;
      const midY = ((src.y ?? 0) + (tgt.y ?? 0)) / 2;

      const fontSize = Math.max(7 / globalScale, 1.5);
      ctx.font = `${fontSize}px Inter, sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillStyle = "rgba(161,161,170,0.6)";
      ctx.fillText(link.label, midX, midY);
    },
    [],
  );

  // Compute unique types for mini legend
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

  return (
    <div className="mt-2 rounded-md border border-border/50">
      {/* Toggle header */}
      <button
        onClick={() => setExpanded((p) => !p)}
        aria-expanded={expanded}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs font-medium text-fg-muted hover:bg-surface-100/50"
      >
        {expanded ? (
          <ChevronDown className="h-3 w-3 shrink-0" />
        ) : (
          <ChevronRight className="h-3 w-3 shrink-0" />
        )}
        <Network className="h-3 w-3 shrink-0 text-brand-400" />
        <span>View source graph</span>
        <Badge variant="info">{explainEvents.length} subgraph{explainEvents.length > 1 ? "s" : ""}</Badge>
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="border-t border-border/50">
          {loading && (
            <div className="flex items-center gap-2 px-3 py-6 text-xs text-fg-subtle">
              <Loader2 className="h-3 w-3 animate-spin" />
              Loading source graph...
            </div>
          )}

          {error !== null && (
            <p className="px-3 py-3 text-xs text-error">
              Failed to load graph: {error}
            </p>
          )}

          {!loading && error === null && graphData.nodes.length === 0 && (
            <p className="px-3 py-4 text-center text-xs text-fg-subtle">
              No graph data available for this query.
            </p>
          )}

          {!loading && graphData.nodes.length > 0 && (
            <>
              {/* Graph info bar */}
              <div className="flex items-center justify-between px-3 py-1.5 text-[10px] text-fg-subtle">
                <span>
                  {graphData.nodes.length} nodes, {graphData.links.length} edges
                </span>
                <button
                  onClick={() => fgRef.current?.zoomToFit(400, 20)}
                  className="rounded p-1 hover:bg-surface-200 hover:text-fg"
                  title="Fit to view"
                  aria-label="Fit to view"
                >
                  <Maximize className="h-3 w-3" />
                </button>
              </div>

              {/* Mini graph canvas */}
              <div
                ref={containerRef}
                className="relative bg-surface-0"
                style={{ height: 280 }}
              >
                <Suspense
                  fallback={
                    <div className="flex h-full items-center justify-center">
                      <Loader2 className="h-4 w-4 animate-spin text-fg-subtle" />
                    </div>
                  }
                >
                  <ForceGraph2D
                    ref={fgRef}
                    graphData={graphData}
                    nodeCanvasObject={paintNode}
                    nodePointerAreaPaint={(node: GraphNode, color, ctx) => {
                      const radius = Math.max(
                        2.5,
                        Math.sqrt(node.degree + 1) * 2,
                      );
                      ctx.beginPath();
                      ctx.arc(
                        node.x ?? 0,
                        node.y ?? 0,
                        radius + 2,
                        0,
                        2 * Math.PI,
                      );
                      ctx.fillStyle = color;
                      ctx.fill();
                    }}
                    linkCanvasObjectMode={() => "after"}
                    linkCanvasObject={paintLink}
                    linkColor={() => "rgba(91,128,255,0.25)"}
                    linkDirectionalArrowLength={3}
                    linkDirectionalArrowRelPos={0.85}
                    backgroundColor="transparent"
                    {...(containerWidth > 0 ? { width: containerWidth } : {})}
                    height={280}
                  />
                </Suspense>
              </div>

              {/* Mini type legend */}
              {uniqueTypes.length > 0 && (
                <div className="flex flex-wrap gap-x-3 gap-y-1 border-t border-border/50 px-3 py-2">
                  {uniqueTypes.slice(0, 8).map(([name]) => (
                    <div key={name} className="flex items-center gap-1.5 text-[10px] text-fg-subtle">
                      <span
                        className="inline-block h-2 w-2 rounded-full"
                        style={{ backgroundColor: hashColor(name) }}
                      />
                      <span>{name}</span>
                    </div>
                  ))}
                  {uniqueTypes.length > 8 && (
                    <span className="text-[10px] text-fg-subtle">
                      +{uniqueTypes.length - 8} more
                    </span>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
