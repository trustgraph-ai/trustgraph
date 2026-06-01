import { lazy, Suspense } from "react";
import { useAtom, useAtomRefresh, useAtomValue } from "@effect/atom-react";
import {
  Rotate3d,
  Search,
  Loader2,
  X,
  Filter,
  RefreshCw,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  flowIdAtom,
  graphTriplesAtom,
  graphViewAtom,
  resultData,
  resultError,
  resultLoading,
  settingsAtom,
} from "@/atoms/workbench";
import type { Triple } from "@trustgraph/client";
import {
  localName,
  triplesToGraph,
  RDFS_LABEL,
  RDF_TYPE,
  termValue,
  type GraphNode,
  type GraphLink,
} from "@/lib/graph-utils";
import type { ForceGraphProps } from "react-force-graph-2d";
import { Badge } from "@/components/ui/badge";

const ForceGraph2D = lazy(() => import("react-force-graph-2d")) as unknown as React.ComponentType<ForceGraphProps<GraphNode, GraphLink>>;

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
  const outbound: { predicate: string; object: string; objectLabel: string }[] = [];
  const inbound: { predicate: string; subject: string; subjectLabel: string }[] = [];

  for (const triple of triples) {
    const subject = termValue(triple.s);
    const predicate = termValue(triple.p);
    const object = termValue(triple.o);
    if (predicate === RDFS_LABEL || predicate === RDF_TYPE) continue;
    if (subject === nodeId) {
      outbound.push({
        predicate: labelMap.get(predicate) ?? localName(predicate),
        object,
        objectLabel: labelMap.get(object) ?? localName(object),
      });
    }
    if (object === nodeId) {
      inbound.push({
        predicate: labelMap.get(predicate) ?? localName(predicate),
        subject,
        subjectLabel: labelMap.get(subject) ?? localName(subject),
      });
    }
  }

  return (
    <aside className="absolute right-4 top-4 z-20 max-h-[calc(100%-2rem)] w-96 overflow-y-auto rounded-lg border border-border bg-surface-50 shadow-xl">
      <div className="flex items-start justify-between gap-3 border-b border-border px-4 py-3">
        <div className="min-w-0">
          <h2 className="truncate text-sm font-semibold text-fg">{label}</h2>
          <p className="break-all font-mono text-[10px] text-fg-subtle">{nodeId}</p>
        </div>
        <button onClick={onClose} aria-label="Close node details" className="rounded p-1 text-fg-subtle hover:bg-surface-200 hover:text-fg">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="space-y-4 p-4">
        {outbound.length > 0 && (
          <section>
            <h3 className="mb-2 text-xs font-medium uppercase tracking-wider text-fg-subtle">Outgoing</h3>
            <div className="space-y-2">
              {outbound.map((edge, index) => (
                <div key={`${edge.object}-${index}`} className="rounded-md bg-surface-100 p-2 text-xs">
                  <p className="text-fg-muted">{edge.predicate}</p>
                  <p className="mt-0.5 break-all font-mono text-fg">{edge.objectLabel}</p>
                </div>
              ))}
            </div>
          </section>
        )}
        {inbound.length > 0 && (
          <section>
            <h3 className="mb-2 text-xs font-medium uppercase tracking-wider text-fg-subtle">Incoming</h3>
            <div className="space-y-2">
              {inbound.map((edge, index) => (
                <div key={`${edge.subject}-${index}`} className="rounded-md bg-surface-100 p-2 text-xs">
                  <p className="text-fg-muted">{edge.predicate}</p>
                  <p className="mt-0.5 break-all font-mono text-fg">{edge.subjectLabel}</p>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </aside>
  );
}

function paintNode(showLabels: boolean) {
  return (node: GraphNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const radius = Math.max(3, Math.sqrt(node.degree + 1) * 2.2);
    const x = node.x ?? 0;
    const y = node.y ?? 0;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, 2 * Math.PI);
    ctx.fillStyle = node.color ?? "#5b80ff";
    ctx.fill();
    if (!showLabels || globalScale < 0.7) return;
    const fontSize = Math.max(10 / globalScale, 2);
    ctx.font = `${fontSize}px Inter, sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    const light = document.documentElement.classList.contains("light");
    ctx.fillStyle = light ? "rgba(24,24,27,0.85)" : "rgba(250,250,250,0.85)";
    ctx.fillText(node.label, x, y + radius + 1);
  };
}

function paintLink(link: GraphLink, ctx: CanvasRenderingContext2D, globalScale: number) {
  if (globalScale < 1.5) return;
  const source = link.source as unknown as GraphNode;
  const target = link.target as unknown as GraphNode;
  if (source.x === undefined || source.y === undefined || target.x === undefined || target.y === undefined) return;
  const midX = (source.x + target.x) / 2;
  const midY = (source.y + target.y) / 2;
  const fontSize = Math.max(8 / globalScale, 2);
  ctx.font = `${fontSize}px Inter, sans-serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillStyle = "rgba(161,161,170,0.65)";
  ctx.fillText(link.label, midX, midY);
}

export default function GraphPage() {
  const flowId = useAtomValue(flowIdAtom);
  const collection = useAtomValue(settingsAtom).collection;
  const [view, setView] = useAtom(graphViewAtom);
  const triplesResult = useAtomValue(graphTriplesAtom({ flowId, collection, limit: view.nodeLimit }));
  const refresh = useAtomRefresh(graphTriplesAtom({ flowId, collection, limit: view.nodeLimit }));
  const triples = resultData(triplesResult, []);
  const loading = resultLoading(triplesResult, triples);
  const error = resultError(triplesResult);
  const { data, labelMap, typeMap } = triplesToGraph(triples);
  const search = view.searchTerm.trim().toLowerCase();
  const graphData = search.length === 0
    ? data
    : (() => {
        const nodes = data.nodes.filter((node) => node.label.toLowerCase().includes(search) || node.id.toLowerCase().includes(search));
        const nodeIds = new Set(nodes.map((node) => node.id));
        return {
          nodes,
          links: data.links.filter((link) => {
            const source = typeof link.source === "string" ? link.source : (link.source as GraphNode).id;
            const target = typeof link.target === "string" ? link.target : (link.target as GraphNode).id;
            return nodeIds.has(source) && nodeIds.has(target);
          }),
        };
      })();
  const selectedNode = view.selectedNodeId !== null
    ? data.nodes.find((node) => node.id === view.selectedNodeId)
    : undefined;
  const uniqueTypes = Array.from(new Set(Array.from(typeMap.values()).map(localName))).sort();

  return (
    <div className="flex h-full flex-col">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <Rotate3d className="h-6 w-6 text-brand-400" />
          <h1 className="text-2xl font-bold text-fg">Graph</h1>
          <Badge>{graphData.nodes.length} nodes</Badge>
          <Badge>{graphData.links.length} edges</Badge>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 rounded-lg border border-border bg-surface-100 px-3 py-2">
            <Search className="h-4 w-4 text-fg-subtle" />
            <input
              value={view.searchTerm}
              onChange={(event) => setView({ ...view, searchTerm: event.target.value })}
              placeholder="Search graph..."
              className="w-48 bg-transparent text-sm text-fg placeholder:text-fg-subtle focus:outline-none"
            />
          </div>
          <select
            value={view.nodeLimit}
            onChange={(event) => setView({ ...view, nodeLimit: Number(event.target.value) })}
            aria-label="Node limit"
            className="rounded-lg border border-border bg-surface-100 px-3 py-2 text-sm text-fg focus:border-brand-500 focus:outline-none"
          >
            {[100, 250, 500, 1000].map((limit) => <option key={limit} value={limit}>{limit}</option>)}
          </select>
          <button
            onClick={refresh}
            disabled={loading}
            aria-label="Refresh graph"
            className="rounded-lg border border-border px-3 py-2 text-fg-muted hover:bg-surface-200 disabled:opacity-40"
          >
            <RefreshCwIcon loading={loading} />
          </button>
        </div>
      </div>

      {error !== null && (
        <p className="mb-4 rounded-lg bg-error/10 px-4 py-2 text-sm text-error">{error}</p>
      )}

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <button
          onClick={() => setView({ ...view, showLabels: !view.showLabels })}
          className={cn("flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1.5 text-xs", view.showLabels ? "bg-brand-600/10 text-brand-400" : "text-fg-muted")}
        >
          <Filter className="h-3.5 w-3.5" />
          Labels
        </button>
        {uniqueTypes.slice(0, 8).map((type) => <Badge key={type} variant="info">{type}</Badge>)}
      </div>

      <div className="relative min-h-0 flex-1 overflow-hidden rounded-lg border border-border bg-surface-50">
        {loading && triples.length === 0 && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-surface-50">
            <Loader2 className="mr-2 h-5 w-5 animate-spin text-fg-subtle" />
            <span className="text-fg-subtle">Loading graph...</span>
          </div>
        )}

        {!loading && graphData.nodes.length === 0 && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center">
            <Rotate3d className="mb-3 h-10 w-10 text-fg-subtle opacity-30" />
            <p className="text-fg-subtle">No graph triples available.</p>
          </div>
        )}

        {graphData.nodes.length > 0 && (
          <Suspense fallback={<div className="flex h-full items-center justify-center text-fg-subtle">Loading graph renderer...</div>}>
            <ForceGraph2D
              graphData={graphData}
              width={900}
              height={650}
              backgroundColor="rgba(0,0,0,0)"
              nodeCanvasObject={paintNode(view.showLabels)}
              linkCanvasObjectMode={() => "after"}
              linkCanvasObject={paintLink}
              linkColor={() => "rgba(120,120,140,0.32)"}
              nodePointerAreaPaint={(node, color, ctx) => {
                ctx.fillStyle = color;
                ctx.beginPath();
                ctx.arc(node.x ?? 0, node.y ?? 0, Math.max(6, Math.sqrt(node.degree + 1) * 3), 0, 2 * Math.PI);
                ctx.fill();
              }}
              onNodeClick={(node) => setView({ ...view, selectedNodeId: node.id, selectedNodeLabel: node.label })}
            />
          </Suspense>
        )}

        {selectedNode !== undefined && view.selectedNodeId !== null && (
          <NodeDetailPanel
            nodeId={view.selectedNodeId}
            label={view.selectedNodeLabel ?? selectedNode.label}
            triples={triples}
            labelMap={labelMap}
            onClose={() => setView({ ...view, selectedNodeId: null, selectedNodeLabel: null })}
          />
        )}
      </div>
    </div>
  );
}

function RefreshCwIcon({ loading }: { loading: boolean }) {
  return loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />;
}
