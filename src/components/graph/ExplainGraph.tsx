import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { ZoomControls } from "./ZoomControls";
import { border, palette, text, withGlow } from "../../theme";

// ── Types ───────────────────────────────────────────────────────────

export interface ExplainGraphNode {
  id: string;
  label: string;
  color?: string;
}

export interface ExplainGraphEdge {
  id: string;
  from: string;
  to: string;
  label: string;
  reasoning?: string;
}

interface LayoutNode extends ExplainGraphNode {
  x: number;
  y: number;
  vx: number;
  vy: number;
}

interface ExplainGraphProps {
  nodes: ExplainGraphNode[];
  edges: ExplainGraphEdge[];
  highlightedNodeIds: string[];
  highlightedEdgeIds: string[];
  onNodeClick?: (nodeId: string) => void;
  onEdgeClick?: (edgeId: string) => void;
}

// ── Simple force layout ─────────────────────────────────────────────

function computeLayout(
  nodes: ExplainGraphNode[],
  edges: ExplainGraphEdge[],
  width: number,
  height: number,
): LayoutNode[] {
  if (nodes.length === 0 || width === 0) return [];

  const cx = width / 2;
  const cy = height / 2;

  // Initial positions: circle layout
  const layoutNodes: LayoutNode[] = nodes.map((n, i) => {
    const angle = (Math.PI * 2 * i) / nodes.length - Math.PI / 2;
    const radius = Math.min(cx, cy) * 0.55;
    return {
      ...n,
      x: cx + Math.cos(angle) * radius,
      y: cy + Math.sin(angle) * radius,
      vx: 0,
      vy: 0,
    };
  });

  // Run simple force simulation
  const iterations = 120;
  const repulsion = 2000;
  const attraction = 0.005;
  const damping = 0.85;
  const centerPull = 0.01;

  const nodeMap = new Map(layoutNodes.map((n, i) => [n.id, i]));

  for (let iter = 0; iter < iterations; iter++) {
    // Repulsion between all pairs
    for (let i = 0; i < layoutNodes.length; i++) {
      for (let j = i + 1; j < layoutNodes.length; j++) {
        const a = layoutNodes[i];
        const b = layoutNodes[j];
        let dx = a.x - b.x;
        let dy = a.y - b.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = repulsion / (dist * dist);
        dx = (dx / dist) * force;
        dy = (dy / dist) * force;
        a.vx += dx;
        a.vy += dy;
        b.vx -= dx;
        b.vy -= dy;
      }
    }

    // Attraction along edges
    for (const edge of edges) {
      const ai = nodeMap.get(edge.from);
      const bi = nodeMap.get(edge.to);
      if (ai === undefined || bi === undefined) continue;
      const a = layoutNodes[ai];
      const b = layoutNodes[bi];
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const fx = dx * attraction;
      const fy = dy * attraction;
      a.vx += fx;
      a.vy += fy;
      b.vx -= fx;
      b.vy -= fy;
    }

    // Center pull
    for (const n of layoutNodes) {
      n.vx += (cx - n.x) * centerPull;
      n.vy += (cy - n.y) * centerPull;
    }

    // Apply velocity
    for (const n of layoutNodes) {
      n.vx *= damping;
      n.vy *= damping;
      n.x += n.vx;
      n.y += n.vy;

      // Keep in bounds with padding
      const pad = 40;
      n.x = Math.max(pad, Math.min(width - pad, n.x));
      n.y = Math.max(pad, Math.min(height - pad, n.y));
    }
  }

  return layoutNodes;
}

// ── Component ───────────────────────────────────────────────────────

export function ExplainGraph({
  nodes,
  edges,
  highlightedNodeIds,
  highlightedEdgeIds,
  onNodeClick,
  onEdgeClick,
}: ExplainGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 });
  const [hovered, setHovered] = useState<string | null>(null);

  // Zoom and pan
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const isPanningRef = useRef(false);
  const lastPanPosRef = useRef({ x: 0, y: 0 });

  // Track container size
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const ro = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        setContainerSize({ width: entry.contentRect.width, height: entry.contentRect.height });
      }
    });
    ro.observe(container);
    return () => ro.disconnect();
  }, []);

  // Layout
  const layoutNodes = useMemo(
    () => computeLayout(nodes, edges, containerSize.width, containerSize.height),
    [nodes, edges, containerSize],
  );

  const nodeMap = useMemo(
    () => new Map(layoutNodes.map(n => [n.id, n])),
    [layoutNodes],
  );

  // Grid lines
  const gridLines = useMemo(() => {
    const lines: React.ReactElement[] = [];
    const { width, height } = containerSize;
    if (width === 0) return lines;
    for (let x = 0; x < width; x += 30) {
      lines.push(<line key={`v-${x}`} x1={x} y1={0} x2={x} y2={height} stroke={border.grid} strokeWidth={0.5} />);
    }
    for (let y = 0; y < height; y += 30) {
      lines.push(<line key={`h-${y}`} x1={0} y1={y} x2={width} y2={y} stroke={border.grid} strokeWidth={0.5} />);
    }
    return lines;
  }, [containerSize]);

  // Zoom
  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    const newZoom = Math.min(4, Math.max(0.25, zoom * delta));
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const cursorX = e.clientX - rect.left;
    const cursorY = e.clientY - rect.top;
    const zoomRatio = newZoom / zoom;
    setPan(p => ({ x: cursorX - (cursorX - p.x) * zoomRatio, y: cursorY - (cursorY - p.y) * zoomRatio }));
    setZoom(newZoom);
  }, [zoom]);

  // Pan
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button === 1 || (e.button === 0 && e.shiftKey)) {
      e.preventDefault();
      isPanningRef.current = true;
      lastPanPosRef.current = { x: e.clientX, y: e.clientY };
    }
  }, []);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isPanningRef.current) return;
    const dx = e.clientX - lastPanPosRef.current.x;
    const dy = e.clientY - lastPanPosRef.current.y;
    lastPanPosRef.current = { x: e.clientX, y: e.clientY };
    setPan(p => ({ x: p.x + dx, y: p.y + dy }));
  }, []);

  const handleMouseUp = useCallback(() => { isPanningRef.current = false; }, []);

  const handleResetView = useCallback(() => { setZoom(1); setPan({ x: 0, y: 0 }); }, []);

  const hasHighlights = highlightedNodeIds.length > 0 || highlightedEdgeIds.length > 0;
  const NODE_R = 10;

  if (containerSize.width === 0) {
    return <div ref={containerRef} style={{ width: "100%", height: "100%" }} />;
  }

  return (
    <div
      ref={containerRef}
      style={{ position: "relative", width: "100%", height: "100%", overflow: "hidden" }}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      <svg
        ref={svgRef}
        width={containerSize.width}
        height={containerSize.height}
        style={{ display: "block", background: "transparent", cursor: isPanningRef.current ? "grabbing" : "default" }}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
      >
        <g>{gridLines}</g>

        <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
          {/* Edges */}
          {edges.map((edge) => {
            const from = nodeMap.get(edge.from);
            const to = nodeMap.get(edge.to);
            if (!from || !to) return null;

            const isHighlighted = highlightedEdgeIds.includes(edge.id);
            const isDimmed = hasHighlights && !isHighlighted;
            const isEdgeHovered = hovered === `edge-${edge.id}`;

            const mx = (from.x + to.x) / 2 + (from.y - to.y) * 0.15;
            const my = (from.y + to.y) / 2 + (to.x - from.x) * 0.15;
            const path = `M ${from.x} ${from.y} Q ${mx} ${my} ${to.x} ${to.y}`;

            const alpha = isDimmed ? 0.15 : isHighlighted || isEdgeHovered ? 0.8 : 0.35;
            const edgeColor = palette.cyan;

            return (
              <g
                key={edge.id}
                style={{ cursor: onEdgeClick ? "pointer" : "default" }}
                onClick={() => onEdgeClick?.(edge.id)}
                onMouseEnter={() => setHovered(`edge-${edge.id}`)}
                onMouseLeave={() => setHovered(null)}
              >
                {/* Wider invisible hit area */}
                <path d={path} stroke="transparent" strokeWidth={12} fill="none" />
                <path
                  d={path}
                  stroke={edgeColor}
                  strokeOpacity={alpha}
                  strokeWidth={isHighlighted || isEdgeHovered ? 2 : 1}
                  fill="none"
                />
                {/* Edge label */}
                <text
                  x={mx}
                  y={my - 6}
                  fill={`rgba(255,255,255,${isDimmed ? 0.15 : isHighlighted || isEdgeHovered ? 0.9 : 0.5})`}
                  fontSize={8}
                  fontFamily="'IBM Plex Mono', monospace"
                  textAnchor="middle"
                >
                  {edge.label}
                </text>
                {/* Arrowhead */}
                {(() => {
                  // Point on curve near the end (t=0.85)
                  const t = 0.85;
                  const ax = (1 - t) * (1 - t) * from.x + 2 * (1 - t) * t * mx + t * t * to.x;
                  const ay = (1 - t) * (1 - t) * from.y + 2 * (1 - t) * t * my + t * t * to.y;
                  const dx = to.x - ax;
                  const dy = to.y - ay;
                  const len = Math.sqrt(dx * dx + dy * dy) || 1;
                  const ux = dx / len;
                  const uy = dy / len;
                  // Arrow tip at edge of node circle
                  const tipX = to.x - ux * NODE_R;
                  const tipY = to.y - uy * NODE_R;
                  const arrowSize = 5;
                  const p1x = tipX - ux * arrowSize + uy * arrowSize * 0.4;
                  const p1y = tipY - uy * arrowSize - ux * arrowSize * 0.4;
                  const p2x = tipX - ux * arrowSize - uy * arrowSize * 0.4;
                  const p2y = tipY - uy * arrowSize + ux * arrowSize * 0.4;
                  return (
                    <polygon
                      points={`${tipX},${tipY} ${p1x},${p1y} ${p2x},${p2y}`}
                      fill={edgeColor}
                      fillOpacity={alpha}
                    />
                  );
                })()}
              </g>
            );
          })}

          {/* Nodes */}
          {layoutNodes.map((node) => {
            const isHighlighted = highlightedNodeIds.includes(node.id);
            const isHovered = hovered === node.id;
            const isDimmed = hasHighlights && !isHighlighted;
            const nodeColor = node.color || palette.blue;
            const alpha = isDimmed ? 0.25 : 1;
            const r = isHighlighted || isHovered ? NODE_R * 1.3 : NODE_R;

            return (
              <g
                key={node.id}
                style={{ cursor: onNodeClick ? "pointer" : "default" }}
                onClick={() => onNodeClick?.(node.id)}
                onMouseEnter={() => setHovered(node.id)}
                onMouseLeave={() => setHovered(null)}
              >
                {/* Glow */}
                {(isHighlighted || isHovered) && (
                  <circle cx={node.x} cy={node.y} r={r + 8} fill={nodeColor} fillOpacity={0.15} />
                )}
                {/* Circle */}
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={r}
                  fill={nodeColor}
                  fillOpacity={alpha * 0.2}
                  stroke={nodeColor}
                  strokeOpacity={alpha}
                  strokeWidth={isHighlighted ? 1.5 : 0.75}
                />
                {/* Label */}
                <text
                  x={node.x}
                  y={node.y + r + 12}
                  fill={`rgba(255,255,255,${alpha * (isHighlighted ? 1 : 0.7)})`}
                  fontSize={isHovered ? 9 : 8}
                  fontWeight={isHighlighted ? "bold" : "normal"}
                  fontFamily="'IBM Plex Sans', sans-serif"
                  textAnchor="middle"
                >
                  {node.label}
                </text>
              </g>
            );
          })}
        </g>
      </svg>

      <ZoomControls
        zoom={zoom}
        onZoomIn={() => setZoom(z => Math.min(4, z * 1.2))}
        onZoomOut={() => setZoom(z => Math.max(0.25, z / 1.2))}
        onReset={handleResetView}
      />

      {/* Empty state */}
      {nodes.length === 0 && (
        <div style={{
          position: "absolute", inset: 0,
          display: "flex", alignItems: "center", justifyContent: "center",
          color: text.hint, fontSize: 13, fontStyle: "italic",
          pointerEvents: "none",
        }}>
          Graph will populate as explain events arrive
        </div>
      )}

      {/* Tooltip */}
      {hovered && !hovered.startsWith("edge-") && (() => {
        const node = nodeMap.get(hovered);
        if (!node) return null;
        return (
          <div style={{
            position: "absolute",
            left: node.x * zoom + pan.x + 20,
            top: node.y * zoom + pan.y - 20,
            background: "rgba(15,15,20,0.95)",
            border: `1px solid ${withGlow(node.color || palette.blue, 0.3)}`,
            borderRadius: 8, padding: "8px 12px",
            pointerEvents: "none", backdropFilter: "blur(12px)", zIndex: 10,
          }}>
            <div style={{ color: node.color || palette.blue, fontWeight: 700, fontSize: 12, fontFamily: "'IBM Plex Mono', monospace" }}>
              {node.label}
            </div>
          </div>
        );
      })()}

      {/* Edge tooltip */}
      {hovered?.startsWith("edge-") && (() => {
        const edgeId = hovered.slice(5);
        const edge = edges.find(e => e.id === edgeId);
        if (!edge) return null;
        const from = nodeMap.get(edge.from);
        const to = nodeMap.get(edge.to);
        if (!from || !to) return null;
        const mx = ((from.x + to.x) / 2) * zoom + pan.x;
        const my = ((from.y + to.y) / 2) * zoom + pan.y;
        return (
          <div style={{
            position: "absolute", left: mx + 15, top: my - 15,
            background: "rgba(15,15,20,0.95)",
            border: `1px solid ${withGlow(palette.cyan, 0.3)}`,
            borderRadius: 8, padding: "8px 12px",
            pointerEvents: "none", backdropFilter: "blur(12px)", zIndex: 10,
            maxWidth: 280,
          }}>
            <div style={{ color: palette.cyan, fontWeight: 700, fontSize: 11, fontFamily: "'IBM Plex Mono', monospace" }}>
              {edge.label}
            </div>
            {edge.reasoning && (
              <div style={{ color: text.muted, fontSize: 10, marginTop: 4, lineHeight: 1.4, fontStyle: "italic" }}>
                {edge.reasoning.length > 150 ? edge.reasoning.slice(0, 150) + "..." : edge.reasoning}
              </div>
            )}
          </div>
        );
      })()}
    </div>
  );
}
