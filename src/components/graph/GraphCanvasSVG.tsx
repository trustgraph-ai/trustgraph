import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import type { DomainKey, Entity, GraphNode, OntologyType, Relationship } from "../../types";
import { ZoomControls } from "./ZoomControls";
import { border } from "../../theme";

interface GraphCanvasSVGProps {
  entities: Entity[];
  relationships: Relationship[];
  ontology: OntologyType;
  highlightedEntities: string[];
  onNodeClick: (node: GraphNode) => void;
  activeFilter: DomainKey | null;
}

const SETTLE_TIME = 10000; // 10 seconds until nodes settle

export function GraphCanvasSVG({ entities, relationships, ontology, highlightedEntities, onNodeClick, activeFilter }: GraphCanvasSVGProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 });
  const [hovered, setHovered] = useState<string | null>(null);
  const [settled, setSettled] = useState(false);
  const [time, setTime] = useState(0);
  const animRef = useRef<number>(0);
  const startTimeRef = useRef<number>(0);
  const lastFrameTimeRef = useRef<number>(0);

  // Zoom and pan state
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const isPanningRef = useRef(false);
  const lastPanPosRef = useRef({ x: 0, y: 0 });

  // Track container size
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const resizeObserver = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        setContainerSize({
          width: entry.contentRect.width,
          height: entry.contentRect.height,
        });
      }
    });

    resizeObserver.observe(container);
    return () => resizeObserver.disconnect();
  }, []);

  // Calculate node positions
  const { nodes, domainPositions } = useMemo(() => {
    if (containerSize.width === 0) return { nodes: [], domainPositions: {} };

    const width = containerSize.width;
    const height = containerSize.height;
    const cx = width / 2;
    const cy = height / 2;

    const domainKeys = Object.keys(ontology);
    const domainPositions: Record<DomainKey, { x: number; y: number }> = {};
    domainKeys.forEach((domain, i) => {
      const angle = (Math.PI * 2 * i) / domainKeys.length - Math.PI / 2;
      const radius = Math.min(cx, cy) * 0.45;
      domainPositions[domain] = {
        x: cx + Math.cos(angle) * radius,
        y: cy + Math.sin(angle) * radius,
      };
    });

    const nodes: GraphNode[] = entities.map((e) => {
      const dp = domainPositions[e.domain];
      const subIdx = ontology[e.domain].subclasses.findIndex((s) => s.id === e.id);
      const total = ontology[e.domain].subclasses.length;
      const angle = ((Math.PI * 2) / total) * subIdx - Math.PI / 2;
      const radius = Math.min(width, height) * 0.1;
      const x = dp.x + Math.cos(angle) * radius;
      const y = dp.y + Math.sin(angle) * radius;
      return {
        ...e,
        x,
        y,
        vx: 0,
        vy: 0,
        targetX: x,
        targetY: y,
        r: 9, // Half size since we're not doing 2x canvas scaling
      };
    });

    return { nodes, domainPositions };
  }, [entities, ontology, containerSize]);

  // Animation loop for breathing effect
  useEffect(() => {
    if (containerSize.width === 0) return;

    startTimeRef.current = performance.now();
    setSettled(false);
    setTime(0);

    const frameInterval = 1000 / 30; // 30fps

    function animate(currentTime: number) {
      if (currentTime - lastFrameTimeRef.current < frameInterval) {
        animRef.current = requestAnimationFrame(animate);
        return;
      }
      lastFrameTimeRef.current = currentTime;

      // Check if should settle
      if (currentTime - startTimeRef.current > SETTLE_TIME) {
        setSettled(true);
        // Continue animation only if there are highlights
        if (highlightedEntities && highlightedEntities.length > 0) {
          setTime(t => t + 0.01);
          animRef.current = requestAnimationFrame(animate);
        }
        return;
      }

      setTime(t => t + 0.01);
      animRef.current = requestAnimationFrame(animate);
    }

    animRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animRef.current);
  }, [containerSize, entities, ontology]);

  // Restart animation when highlights change
  useEffect(() => {
    if (highlightedEntities && highlightedEntities.length > 0 && settled && animRef.current === 0) {
      const frameInterval = 1000 / 30;

      function animate(currentTime: number) {
        if (currentTime - lastFrameTimeRef.current < frameInterval) {
          animRef.current = requestAnimationFrame(animate);
          return;
        }
        lastFrameTimeRef.current = currentTime;
        setTime(t => t + 0.01);

        if (highlightedEntities && highlightedEntities.length > 0) {
          animRef.current = requestAnimationFrame(animate);
        } else {
          animRef.current = 0;
        }
      }

      animRef.current = requestAnimationFrame(animate);
    }
  }, [highlightedEntities, settled]);

  // Generate grid lines
  const gridLines = useMemo(() => {
    const lines: React.ReactElement[] = [];
    const { width, height } = containerSize;
    if (width === 0) return lines;

    for (let x = 0; x < width; x += 30) {
      lines.push(
        <line key={`v-${x}`} x1={x} y1={0} x2={x} y2={height} stroke={border.grid} strokeWidth={0.5} />
      );
    }
    for (let y = 0; y < height; y += 30) {
      lines.push(
        <line key={`h-${y}`} x1={0} y1={y} x2={width} y2={y} stroke={border.grid} strokeWidth={0.5} />
      );
    }
    return lines;
  }, [containerSize]);

  // Calculate edge path with curve
  const getEdgePath = useCallback((fromNode: GraphNode, toNode: GraphNode, time: number, isSettled: boolean) => {
    const driftX1 = isSettled ? 0 : Math.sin(time + fromNode.targetX * 0.01) * 0.3;
    const driftY1 = isSettled ? 0 : Math.cos(time + fromNode.targetY * 0.01) * 0.3;
    const driftX2 = isSettled ? 0 : Math.sin(time + toNode.targetX * 0.01) * 0.3;
    const driftY2 = isSettled ? 0 : Math.cos(time + toNode.targetY * 0.01) * 0.3;

    const x1 = fromNode.x + driftX1;
    const y1 = fromNode.y + driftY1;
    const x2 = toNode.x + driftX2;
    const y2 = toNode.y + driftY2;

    const mx = (x1 + x2) / 2 + (y1 - y2) * 0.1;
    const my = (y1 + y2) / 2 + (x2 - x1) * 0.1;

    return { path: `M ${x1} ${y1} Q ${mx} ${my} ${x2} ${y2}`, mx, my, x1, y1, x2, y2 };
  }, []);

  // Get node position with drift
  const getNodePosition = useCallback((node: GraphNode, time: number, isSettled: boolean) => {
    if (isSettled) {
      return { x: node.x, y: node.y };
    }
    const driftX = Math.sin(time + node.targetX * 0.01) * 0.3;
    const driftY = Math.cos(time + node.targetY * 0.01) * 0.3;
    return { x: node.x + driftX, y: node.y + driftY };
  }, []);

  const handleNodeClick = useCallback((node: GraphNode) => {
    onNodeClick(node);
  }, [onNodeClick]);

  // Zoom handler - zoom towards cursor position
  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    const newZoom = Math.min(4, Math.max(0.25, zoom * delta));

    // Get cursor position relative to SVG
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const cursorX = e.clientX - rect.left;
    const cursorY = e.clientY - rect.top;

    // Adjust pan to zoom towards cursor
    const zoomRatio = newZoom / zoom;
    const newPanX = cursorX - (cursorX - pan.x) * zoomRatio;
    const newPanY = cursorY - (cursorY - pan.y) * zoomRatio;

    setZoom(newZoom);
    setPan({ x: newPanX, y: newPanY });
  }, [zoom, pan]);

  // Pan handlers
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    // Only pan with middle mouse or when holding space (we'll just use middle mouse for now)
    if (e.button === 1 || e.button === 0 && e.shiftKey) {
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

  const handleMouseUp = useCallback(() => {
    isPanningRef.current = false;
  }, []);

  // Reset zoom/pan
  const handleResetView = useCallback(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }, []);

  if (containerSize.width === 0) {
    return <div ref={containerRef} style={{ width: "100%", height: "100%" }} />;
  }

  const filteredRels = activeFilter
    ? relationships.filter((r) => r.domain.includes(activeFilter))
    : relationships;

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
        {/* Grid - outside transform so it stays fixed */}
        <g>{gridLines}</g>

        {/* Transformed content */}
        <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>

        {/* Domain labels */}
        <g>
          {(Object.entries(domainPositions) as [DomainKey, { x: number; y: number }][]).map(([domain, pos]) => {
            const data = ontology[domain];
            return (
              <text
                key={domain}
                x={pos.x}
                y={pos.y - Math.min(containerSize.width, containerSize.height) * 0.14}
                fill={data.color + "44"}
                fontSize={11}
                fontWeight="bold"
                fontFamily="'IBM Plex Mono', monospace"
                textAnchor="middle"
              >
                {data.label.toUpperCase()}
              </text>
            );
          })}
        </g>

        {/* Edges */}
        <g>
          {filteredRels.map((rel, i) => {
            const fromNode = nodes.find((n) => n.id === rel.from);
            const toNode = nodes.find((n) => n.id === rel.to);
            if (!fromNode || !toNode) return null;

            const isHighlighted =
              highlightedEntities &&
              highlightedEntities.includes(rel.from) &&
              highlightedEntities.includes(rel.to);

            const { path, mx, my, x1, y1, x2, y2 } = getEdgePath(fromNode, toNode, time, settled);
            const baseAlpha = isHighlighted ? 0.7 : 0.12;
            const pulse = isHighlighted ? Math.sin(time * 4) * 0.15 + 0.15 : 0;
            const alpha = Math.min(1, baseAlpha + pulse);

            // Particle position on curve (quadratic bezier)
            const t = (time * 2) % 1;
            const px = (1 - t) * (1 - t) * x1 + 2 * (1 - t) * t * mx + t * t * x2;
            const py = (1 - t) * (1 - t) * y1 + 2 * (1 - t) * t * my + t * t * y2;

            return (
              <g key={`${rel.from}-${rel.predicate}-${rel.to}-${i}`}>
                <defs>
                  <linearGradient id={`grad-${rel.from}-${rel.to}-${i}`} x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor={fromNode.color} stopOpacity={alpha} />
                    <stop offset="100%" stopColor={toNode.color} stopOpacity={alpha} />
                  </linearGradient>
                </defs>
                <path
                  d={path}
                  stroke={`url(#grad-${rel.from}-${rel.to}-${i})`}
                  strokeWidth={isHighlighted ? 1.5 : 0.75}
                  fill="none"
                />
                {isHighlighted && (
                  <circle cx={px} cy={py} r={1.5} fill="#fff" />
                )}
              </g>
            );
          })}
        </g>

        {/* Nodes */}
        <g>
          {nodes.map((node) => {
            const isHighlighted = highlightedEntities && highlightedEntities.includes(node.id);
            const isHovered = hovered === node.id;
            const isDimmed = highlightedEntities && highlightedEntities.length > 0 && !isHighlighted;
            const isFiltered = activeFilter && node.domain !== activeFilter && !relationships.some(
              r => r.domain.includes(activeFilter) && (r.from === node.id || r.to === node.id)
            );

            const alpha = isFiltered ? 0.15 : isDimmed ? 0.3 : 1;
            const r = isHighlighted || isHovered ? node.r * 1.4 : node.r;
            const pulseR = isHighlighted && !settled ? Math.sin(time * 3) * 1.5 : 0;
            const { x, y } = getNodePosition(node, time, settled);

            return (
              <g
                key={node.id}
                style={{ cursor: "pointer" }}
                onClick={() => handleNodeClick(node)}
                onMouseEnter={() => setHovered(node.id)}
                onMouseLeave={() => setHovered(null)}
              >
                {/* Glow */}
                {(isHighlighted || isHovered) && !isFiltered && (
                  <circle
                    cx={x}
                    cy={y}
                    r={r + 6 + pulseR}
                    fill="url(#glow)"
                    opacity={0.5}
                  >
                    <defs>
                      <radialGradient id={`glow-${node.id}`}>
                        <stop offset="0%" stopColor={node.color} stopOpacity={0.4} />
                        <stop offset="100%" stopColor={node.color} stopOpacity={0} />
                      </radialGradient>
                    </defs>
                  </circle>
                )}

                {/* Node circle */}
                <circle
                  cx={x}
                  cy={y}
                  r={r}
                  fill={node.color}
                  fillOpacity={alpha * 0.2}
                  stroke={node.color}
                  strokeOpacity={alpha}
                  strokeWidth={isHighlighted ? 1.25 : 0.75}
                />

                {/* Label */}
                <text
                  x={x}
                  y={y + r + 9}
                  fill={`rgba(255,255,255,${alpha * (isHighlighted ? 1 : 0.75)})`}
                  fontSize={isHovered ? 8.5 : 7}
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
        </g>{/* Close transform group */}
      </svg>

      <ZoomControls
        zoom={zoom}
        onZoomIn={() => setZoom(z => Math.min(4, z * 1.2))}
        onZoomOut={() => setZoom(z => Math.max(0.25, z / 1.2))}
        onReset={handleResetView}
      />

      {/* Tooltip */}
      {hovered && (() => {
        const node = nodes.find((n) => n.id === hovered);
        if (!node) return null;
        const { x, y } = getNodePosition(node, time, settled);
        return (
          <div style={{
            position: "absolute", left: x + 20, top: y - 20,
            background: "rgba(15,15,20,0.95)", border: `1px solid ${node.color}44`,
            borderRadius: 8, padding: "10px 14px", pointerEvents: "none",
            backdropFilter: "blur(12px)", zIndex: 10, minWidth: 180,
          }}>
            <div style={{ color: node.color, fontWeight: 700, fontSize: 13, fontFamily: "'IBM Plex Mono', monospace" }}>
              {node.icon} {node.label}
            </div>
            <div style={{ color: "#888", fontSize: 11, marginTop: 4, fontFamily: "'IBM Plex Mono', monospace" }}>
              {Object.entries(node.props || {}).map(([k, v]) => (
                <div key={k}><span style={{ color: "#666" }}>{k}:</span> <span style={{ color: "#ccc" }}>{String(v)}</span></div>
              ))}
            </div>
          </div>
        );
      })()}
    </div>
  );
}
