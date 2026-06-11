import { lazy, Suspense } from "react";
import { useAtom, useAtomValue } from "@effect/atom-react";
import { Network, ChevronRight, ChevronDown, Loader2 } from "lucide-react";
import * as Atom from "effect/unstable/reactivity/Atom";
import {
  explainTriplesAtom,
  flowIdAtom,
  resultData,
  resultError,
  resultLoading,
} from "@/atoms/workbench";
import type {
  GraphNode,
  GraphLink,
} from "@/lib/graph-utils";
import {
  triplesToGraph,
  localName,
  directedGraphLinkProps,
  DEFAULT_GRAPH_NODE_COLOR,
} from "@/lib/graph-utils";
import type { ExplainEvent } from "@trustgraph/client";
import type { ForceGraphProps } from "react-force-graph-2d";
import type * as React from "react";
import { Badge } from "@/components/ui/badge";

const ForceGraph2D = lazy(() => import("react-force-graph-2d")) as unknown as React.ComponentType<ForceGraphProps<GraphNode, GraphLink>>;
const explainExpandedAtom = Atom.make<Record<string, boolean>>({}).pipe(Atom.keepAlive);

interface ExplainGraphProps {
  explainEvents: ExplainEvent[];
  collection: string;
}

function paintNode(node: GraphNode, ctx: CanvasRenderingContext2D, globalScale: number) {
  const radius = Math.max(2.5, Math.sqrt(node.degree + 1) * 2);
  const x = node.x ?? 0;
  const y = node.y ?? 0;
  ctx.beginPath();
  ctx.arc(x, y, radius, 0, 2 * Math.PI);
  ctx.fillStyle = node.color ?? DEFAULT_GRAPH_NODE_COLOR;
  ctx.fill();
  const fontSize = Math.max(9 / globalScale, 1.5);
  ctx.font = `${fontSize}px Inter, sans-serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  const isLight = document.documentElement.classList.contains("light");
  ctx.fillStyle = isLight ? "rgba(24,24,27,0.85)" : "rgba(250,250,250,0.85)";
  ctx.fillText(node.label, x, y + radius + 1);
}

function paintLink(link: GraphLink, ctx: CanvasRenderingContext2D, globalScale: number) {
  if (globalScale < 1.5) return;
  const source = link.source as unknown as GraphNode;
  const target = link.target as unknown as GraphNode;
  if (source.x === undefined || source.y === undefined || target.x === undefined || target.y === undefined) return;
  const midX = (source.x + target.x) / 2;
  const midY = (source.y + target.y) / 2;
  const fontSize = Math.max(7 / globalScale, 1.5);
  ctx.font = `${fontSize}px Inter, sans-serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillStyle = "rgba(161,161,170,0.6)";
  ctx.fillText(link.label, midX, midY);
}

export function ExplainGraph({ explainEvents, collection }: ExplainGraphProps) {
  const flowId = useAtomValue(flowIdAtom);
  const [expandedMap, setExpandedMap] = useAtom(explainExpandedAtom);
  const key = `${flowId}:${collection}:${explainEvents.map((event) => event.explainGraph ?? event.explainId).join("|")}`;
  const expanded = expandedMap[key];
  const result = useAtomValue(explainTriplesAtom({ events: explainEvents, flowId, collection }));
  const triples = resultData(result, []);
  const loading = expanded && resultLoading(result, triples);
  const error = resultError(result);
  const { data: graphData, typeMap } = triplesToGraph(triples);
  const uniqueTypes = Array.from(new Set(Array.from(typeMap.values()).map(localName))).sort();

  return (
    <div className="mt-2 rounded-md border border-border/50">
      <button
        onClick={() => setExpandedMap({ ...expandedMap, [key]: !expanded })}
        aria-expanded={expanded}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs font-medium text-fg-muted hover:bg-surface-100/50"
      >
        {expanded ? <ChevronDown className="h-3 w-3 shrink-0" /> : <ChevronRight className="h-3 w-3 shrink-0" />}
        <Network className="h-3 w-3 shrink-0 text-brand-400" />
        <span>View source graph</span>
        <Badge variant="info">{explainEvents.length} subgraph{explainEvents.length > 1 ? "s" : ""}</Badge>
      </button>

      {expanded && (
        <div className="border-t border-border/50">
          {loading && (
            <div className="flex items-center gap-2 px-3 py-6 text-xs text-fg-subtle">
              <Loader2 className="h-3 w-3 animate-spin" />
              Loading source graph...
            </div>
          )}
          {error !== null && <p className="px-3 py-3 text-xs text-error">Failed to load graph: {error}</p>}
          {!loading && error === null && graphData.nodes.length === 0 && (
            <p className="px-3 py-4 text-center text-xs text-fg-subtle">No graph data available for this query.</p>
          )}
          {!loading && graphData.nodes.length > 0 && (
            <>
              <div className="flex items-center justify-between px-3 py-1.5 text-[10px] text-fg-subtle">
                <span>{graphData.nodes.length} nodes, {graphData.links.length} edges</span>
                <div className="flex gap-1">
                  {uniqueTypes.slice(0, 4).map((type) => <Badge key={type} variant="info">{type}</Badge>)}
                </div>
              </div>
              <div className="relative h-[280px] overflow-hidden bg-surface-0">
                <Suspense fallback={<div className="flex h-full items-center justify-center text-xs text-fg-subtle">Loading graph...</div>}>
                  <ForceGraph2D
                    graphData={graphData}
                    width={600}
                    height={280}
                    backgroundColor="rgba(0,0,0,0)"
                    nodeCanvasObject={paintNode}
                    linkCanvasObjectMode={() => "after"}
                    linkCanvasObject={paintLink}
                    {...directedGraphLinkProps}
                  />
                </Suspense>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
