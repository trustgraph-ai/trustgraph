import { useState, useEffect, useRef, useCallback, useMemo } from "react";

// ═══════════════════════════════════════════════════════════════════
// TRUSTGRAPH RETAIL INTELLIGENCE DEMO
// Ontology-Driven Context Graph: Consumer × Agent × Retail × Brand
// ═══════════════════════════════════════════════════════════════════

// ── Ontology Schema ──────────────────────────────────────────────
const ONTOLOGY = {
  consumer: {
    label: "Consumer",
    color: "#6EE7B7",
    glow: "rgba(110,231,183,0.4)",
    icon: "👤",
    description: "Individuals and segments interacting with brands through retail channels",
    properties: ["segment", "preferences", "journeyStage", "lifetime_value", "sentiment"],
    subclasses: [
      { id: "cs1", label: "Urban Millennials", props: { size: "2.4M", avgSpend: "$142/mo", loyalty: 0.78, journeyStage: "Engaged" } },
      { id: "cs2", label: "Active Families", props: { size: "1.8M", avgSpend: "$218/mo", loyalty: 0.85, journeyStage: "Loyal" } },
      { id: "cs3", label: "Eco-Conscious Gen Z", props: { size: "3.1M", avgSpend: "$96/mo", loyalty: 0.62, journeyStage: "Exploring" } },
      { id: "cs4", label: "Luxury Seekers", props: { size: "890K", avgSpend: "$384/mo", loyalty: 0.91, journeyStage: "Advocate" } },
      { id: "cs5", label: "Weekend Warriors", props: { size: "1.5M", avgSpend: "$167/mo", loyalty: 0.73, journeyStage: "Engaged" } },
    ],
  },
  brand: {
    label: "Brand",
    color: "#F9A8D4",
    glow: "rgba(249,168,212,0.4)",
    icon: "✦",
    description: "Product brands seeking to connect with consumers through retail experiences",
    properties: ["identity", "positioning", "campaigns", "products", "partnerships"],
    subclasses: [
      { id: "br1", label: "Lumière Beauty", props: { category: "Cosmetics", positioning: "Premium", campaigns: 12, sentiment: 0.87 } },
      { id: "br2", label: "Nordic Trail", props: { category: "Outdoor Apparel", positioning: "Sustainable", campaigns: 8, sentiment: 0.82 } },
      { id: "br3", label: "Velo Sport", props: { category: "Athletics", positioning: "Performance", campaigns: 15, sentiment: 0.79 } },
      { id: "br4", label: "Casa Verde", props: { category: "Home & Living", positioning: "Artisanal", campaigns: 6, sentiment: 0.90 } },
      { id: "br5", label: "Artisan Coffee Co.", props: { category: "F&B", positioning: "Community", campaigns: 10, sentiment: 0.85 } },
    ],
  },
  retail: {
    label: "Retail",
    color: "#93C5FD",
    glow: "rgba(147,197,253,0.4)",
    icon: "🏬",
    description: "Channels, touchpoints, and experiences where brands meet consumers",
    properties: ["channel", "location", "traffic", "conversionRate", "experience_score"],
    subclasses: [
      { id: "rt1", label: "Flagship Store NYC", props: { channel: "Physical", traffic: "48K/mo", conversion: "12.3%", experience: 0.91 } },
      { id: "rt2", label: "Mobile Commerce App", props: { channel: "Digital", traffic: "1.2M/mo", conversion: "4.7%", experience: 0.78 } },
      { id: "rt3", label: "Pop-Up Experience", props: { channel: "Experiential", traffic: "8K/event", conversion: "18.6%", experience: 0.95 } },
      { id: "rt4", label: "Social Commerce", props: { channel: "Social", traffic: "890K/mo", conversion: "3.2%", experience: 0.72 } },
      { id: "rt5", label: "Loyalty Hub", props: { channel: "Omnichannel", traffic: "340K/mo", conversion: "22.1%", experience: 0.88 } },
    ],
  },
  agent: {
    label: "Agent",
    color: "#FCD34D",
    glow: "rgba(252,211,77,0.4)",
    icon: "⚡",
    description: "AI agents that orchestrate personalized brand-consumer connections",
    properties: ["capability", "contextSources", "accuracy", "latency", "decisions_per_day"],
    subclasses: [
      { id: "ag1", label: "Recommendation Agent", props: { capability: "Product Discovery", accuracy: "94.2%", latency: "120ms", decisions: "2.1M/day" } },
      { id: "ag2", label: "Personalization Agent", props: { capability: "Experience Tailoring", accuracy: "91.8%", latency: "85ms", decisions: "890K/day" } },
      { id: "ag3", label: "Campaign Orchestrator", props: { capability: "Brand Activation", accuracy: "88.5%", latency: "200ms", decisions: "340K/day" } },
      { id: "ag4", label: "Sentiment Analyst", props: { capability: "Brand Perception", accuracy: "96.1%", latency: "150ms", decisions: "1.5M/day" } },
      { id: "ag5", label: "Journey Optimizer", props: { capability: "Path Optimization", accuracy: "89.7%", latency: "180ms", decisions: "560K/day" } },
    ],
  },
};

// ── Ontology Relationships (Triples) ──────────────────────────────
const RELATIONSHIPS = [
  // Consumer ↔ Brand
  { from: "cs1", to: "br1", predicate: "has_affinity_for", strength: 0.85, domain: ["consumer", "brand"] },
  { from: "cs1", to: "br5", predicate: "frequents", strength: 0.69, domain: ["consumer", "brand"] },
  { from: "cs2", to: "br2", predicate: "has_affinity_for", strength: 0.78, domain: ["consumer", "brand"] },
  { from: "cs2", to: "br3", predicate: "purchases_from", strength: 0.88, domain: ["consumer", "brand"] },
  { from: "cs3", to: "br2", predicate: "advocates_for", strength: 0.71, domain: ["consumer", "brand"] },
  { from: "cs3", to: "br4", predicate: "has_affinity_for", strength: 0.65, domain: ["consumer", "brand"] },
  { from: "cs3", to: "br5", predicate: "frequents", strength: 0.58, domain: ["consumer", "brand"] },
  { from: "cs4", to: "br1", predicate: "loyal_to", strength: 0.92, domain: ["consumer", "brand"] },
  { from: "cs4", to: "br4", predicate: "purchases_from", strength: 0.82, domain: ["consumer", "brand"] },
  { from: "cs5", to: "br3", predicate: "has_affinity_for", strength: 0.76, domain: ["consumer", "brand"] },
  { from: "cs5", to: "br5", predicate: "frequents", strength: 0.74, domain: ["consumer", "brand"] },
  // Consumer ↔ Retail
  { from: "cs1", to: "rt2", predicate: "shops_via", strength: 0.82, domain: ["consumer", "retail"] },
  { from: "cs1", to: "rt4", predicate: "discovers_through", strength: 0.71, domain: ["consumer", "retail"] },
  { from: "cs2", to: "rt1", predicate: "shops_via", strength: 0.85, domain: ["consumer", "retail"] },
  { from: "cs2", to: "rt5", predicate: "member_of", strength: 0.90, domain: ["consumer", "retail"] },
  { from: "cs3", to: "rt3", predicate: "experiences", strength: 0.88, domain: ["consumer", "retail"] },
  { from: "cs3", to: "rt4", predicate: "discovers_through", strength: 0.79, domain: ["consumer", "retail"] },
  { from: "cs4", to: "rt1", predicate: "shops_via", strength: 0.94, domain: ["consumer", "retail"] },
  { from: "cs4", to: "rt3", predicate: "experiences", strength: 0.86, domain: ["consumer", "retail"] },
  { from: "cs5", to: "rt2", predicate: "shops_via", strength: 0.72, domain: ["consumer", "retail"] },
  { from: "cs5", to: "rt5", predicate: "member_of", strength: 0.68, domain: ["consumer", "retail"] },
  // Brand ↔ Retail
  { from: "br1", to: "rt1", predicate: "merchandises_in", strength: 0.90, domain: ["brand", "retail"] },
  { from: "br1", to: "rt3", predicate: "activates_via", strength: 0.85, domain: ["brand", "retail"] },
  { from: "br2", to: "rt3", predicate: "activates_via", strength: 0.82, domain: ["brand", "retail"] },
  { from: "br2", to: "rt4", predicate: "promotes_on", strength: 0.75, domain: ["brand", "retail"] },
  { from: "br3", to: "rt2", predicate: "sells_through", strength: 0.80, domain: ["brand", "retail"] },
  { from: "br3", to: "rt5", predicate: "rewards_via", strength: 0.77, domain: ["brand", "retail"] },
  { from: "br4", to: "rt1", predicate: "merchandises_in", strength: 0.88, domain: ["brand", "retail"] },
  { from: "br4", to: "rt4", predicate: "promotes_on", strength: 0.70, domain: ["brand", "retail"] },
  { from: "br5", to: "rt3", predicate: "activates_via", strength: 0.79, domain: ["brand", "retail"] },
  { from: "br5", to: "rt5", predicate: "rewards_via", strength: 0.83, domain: ["brand", "retail"] },
  // Agent ↔ Consumer
  { from: "ag1", to: "cs1", predicate: "recommends_to", strength: 0.87, domain: ["agent", "consumer"] },
  { from: "ag1", to: "cs3", predicate: "recommends_to", strength: 0.81, domain: ["agent", "consumer"] },
  { from: "ag2", to: "cs4", predicate: "personalizes_for", strength: 0.93, domain: ["agent", "consumer"] },
  { from: "ag2", to: "cs2", predicate: "personalizes_for", strength: 0.84, domain: ["agent", "consumer"] },
  { from: "ag4", to: "cs1", predicate: "monitors_sentiment_of", strength: 0.78, domain: ["agent", "consumer"] },
  { from: "ag4", to: "cs3", predicate: "monitors_sentiment_of", strength: 0.82, domain: ["agent", "consumer"] },
  { from: "ag5", to: "cs2", predicate: "optimizes_journey_for", strength: 0.86, domain: ["agent", "consumer"] },
  { from: "ag5", to: "cs5", predicate: "optimizes_journey_for", strength: 0.75, domain: ["agent", "consumer"] },
  // Agent ↔ Brand
  { from: "ag3", to: "br1", predicate: "orchestrates_campaign_for", strength: 0.88, domain: ["agent", "brand"] },
  { from: "ag3", to: "br2", predicate: "orchestrates_campaign_for", strength: 0.82, domain: ["agent", "brand"] },
  { from: "ag3", to: "br5", predicate: "orchestrates_campaign_for", strength: 0.79, domain: ["agent", "brand"] },
  { from: "ag4", to: "br1", predicate: "analyzes_perception_of", strength: 0.91, domain: ["agent", "brand"] },
  { from: "ag4", to: "br3", predicate: "analyzes_perception_of", strength: 0.85, domain: ["agent", "brand"] },
  { from: "ag1", to: "br3", predicate: "curates_products_for", strength: 0.83, domain: ["agent", "brand"] },
  { from: "ag1", to: "br4", predicate: "curates_products_for", strength: 0.77, domain: ["agent", "brand"] },
  // Agent ↔ Retail
  { from: "ag2", to: "rt1", predicate: "tailors_experience_at", strength: 0.89, domain: ["agent", "retail"] },
  { from: "ag2", to: "rt2", predicate: "tailors_experience_at", strength: 0.85, domain: ["agent", "retail"] },
  { from: "ag3", to: "rt3", predicate: "deploys_campaign_at", strength: 0.81, domain: ["agent", "retail"] },
  { from: "ag3", to: "rt4", predicate: "deploys_campaign_at", strength: 0.86, domain: ["agent", "retail"] },
  { from: "ag5", to: "rt1", predicate: "optimizes_flow_at", strength: 0.84, domain: ["agent", "retail"] },
  { from: "ag5", to: "rt5", predicate: "optimizes_flow_at", strength: 0.80, domain: ["agent", "retail"] },
];

// ── Pre-built Agent Queries & Responses ────────────────────────────
const DEMO_QUERIES = [
  {
    q: "Which brands should activate at the Pop-Up Experience to reach Eco-Conscious Gen Z?",
    thinking: [
      "Traversing ontology: Consumer[cs3] → has_affinity_for → Brand[br2, br4, br5]",
      "Traversing ontology: Consumer[cs3] → experiences → Retail[rt3]",
      "Cross-referencing: Brand activations at Retail[rt3]",
      "Ranking by: affinity strength × activation fit × conversion potential",
    ],
    answer: "Nordic Trail and Artisan Coffee Co. are the strongest activation candidates for the Pop-Up Experience targeting Eco-Conscious Gen Z. Nordic Trail's sustainability positioning aligns with this segment's values (affinity: 0.71) and already activates via experiential retail (strength: 0.82). Artisan Coffee Co. has existing frequency with this segment (0.58) and pop-up activation experience (0.79). Casa Verde is a secondary candidate — lower affinity (0.65) but high experiential fit.",
    entities: ["cs3", "br2", "br5", "br4", "rt3"],
    triples: 8,
  },
  {
    q: "How should Lumière Beauty optimize its engagement with Luxury Seekers across channels?",
    thinking: [
      "Resolving entities: Brand[br1] = Lumière Beauty, Consumer[cs4] = Luxury Seekers",
      "Traversing: Brand[br1] → merchandises_in → Retail[rt1], activates_via → Retail[rt3]",
      "Traversing: Consumer[cs4] → shops_via → Retail[rt1], experiences → Retail[rt3]",
      "Agent context: Personalization Agent[ag2] → personalizes_for → Consumer[cs4] (0.93)",
      "Aggregating channel overlap and engagement signals",
    ],
    answer: "Lumière Beauty has exceptional alignment with Luxury Seekers — the strongest brand-consumer affinity in the graph (0.92). Both converge on Flagship Store NYC and Pop-Up Experiences. The Personalization Agent already achieves 93% accuracy for this segment. Recommendation: Deepen the flagship in-store experience with agent-powered personalized consultations, and create exclusive pop-up previews. The loyalty-to-advocacy pipeline is strong (journey stage: Advocate) — leverage this for referral programs through the Loyalty Hub.",
    entities: ["br1", "cs4", "rt1", "rt3", "ag2", "rt5"],
    triples: 12,
  },
  {
    q: "What's the optimal agent configuration for the Mobile Commerce channel?",
    thinking: [
      "Resolving: Retail[rt2] = Mobile Commerce App",
      "Traversing: Agent → tailors_experience_at → Retail[rt2]",
      "Traversing: Consumer → shops_via → Retail[rt2]: [cs1, cs5]",
      "Traversing: Brand → sells_through → Retail[rt2]: [br3]",
      "Evaluating agent capabilities against mobile channel requirements",
    ],
    answer: "Mobile Commerce currently has the Personalization Agent deployed (experience tailoring, 85% strength). Primary consumer segments are Urban Millennials (0.82) and Weekend Warriors (0.72). Add the Recommendation Agent — it already serves Urban Millennials (0.87) and can curate Velo Sport products (the channel's primary brand). The Journey Optimizer should be connected to reduce the gap between the channel's high traffic (1.2M/mo) and moderate conversion (4.7%). Projected improvement: 2.1% conversion lift through graph-informed product sequencing.",
    entities: ["rt2", "ag2", "ag1", "ag5", "cs1", "cs5", "br3"],
    triples: 11,
  },
];

// ── Helper: find all entities ────────────────────────────────────────
function getAllEntities() {
  const all = [];
  Object.entries(ONTOLOGY).forEach(([domain, data]) => {
    data.subclasses.forEach((sc) => {
      all.push({ ...sc, domain, color: data.color, glow: data.glow, icon: data.icon });
    });
  });
  return all;
}

// ── Graph Visualization (Canvas-based force layout) ─────────────────
function GraphCanvas({ highlightedEntities, onNodeClick, activeFilter }) {
  const canvasRef = useRef(null);
  const nodesRef = useRef([]);
  const animRef = useRef(null);
  const hoveredRef = useRef(null);
  const [hovered, setHovered] = useState(null);

  const entities = useMemo(() => getAllEntities(), []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width * 2;
    canvas.height = rect.height * 2;
    canvas.style.width = rect.width + "px";
    canvas.style.height = rect.height + "px";

    const cx = canvas.width / 2;
    const cy = canvas.height / 2;

    // Position nodes in domain clusters
    const domainPositions = {
      consumer: { x: cx - cx * 0.35, y: cy - cy * 0.32 },
      brand: { x: cx + cx * 0.35, y: cy - cy * 0.32 },
      retail: { x: cx + cx * 0.35, y: cy + cy * 0.32 },
      agent: { x: cx - cx * 0.35, y: cy + cy * 0.32 },
    };

    nodesRef.current = entities.map((e, i) => {
      const dp = domainPositions[e.domain];
      const subIdx = ONTOLOGY[e.domain].subclasses.findIndex((s) => s.id === e.id);
      const total = ONTOLOGY[e.domain].subclasses.length;
      const angle = ((Math.PI * 2) / total) * subIdx - Math.PI / 2;
      const radius = Math.min(canvas.width, canvas.height) * 0.1;
      return {
        ...e,
        x: dp.x + Math.cos(angle) * radius,
        y: dp.y + Math.sin(angle) * radius,
        vx: 0,
        vy: 0,
        targetX: dp.x + Math.cos(angle) * radius,
        targetY: dp.y + Math.sin(angle) * radius,
        r: 18,
      };
    });

    const ctx = canvas.getContext("2d");
    let time = 0;

    function draw() {
      time += 0.005;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Subtle grid
      ctx.strokeStyle = "rgba(255,255,255,0.015)";
      ctx.lineWidth = 1;
      for (let x = 0; x < canvas.width; x += 60) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke();
      }
      for (let y = 0; y < canvas.height; y += 60) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke();
      }

      // Domain labels
      Object.entries(domainPositions).forEach(([domain, pos]) => {
        const data = ONTOLOGY[domain];
        ctx.font = "bold 22px 'IBM Plex Mono', monospace";
        ctx.fillStyle = data.color + "44";
        ctx.textAlign = "center";
        ctx.fillText(data.label.toUpperCase(), pos.x, pos.y - Math.min(canvas.width, canvas.height) * 0.14);
      });

      // Draw edges
      const nodes = nodesRef.current;
      const filteredRels = activeFilter
        ? RELATIONSHIPS.filter((r) => r.domain.includes(activeFilter))
        : RELATIONSHIPS;

      filteredRels.forEach((rel) => {
        const fromNode = nodes.find((n) => n.id === rel.from);
        const toNode = nodes.find((n) => n.id === rel.to);
        if (!fromNode || !toNode) return;

        const isHighlighted =
          highlightedEntities &&
          highlightedEntities.includes(rel.from) &&
          highlightedEntities.includes(rel.to);

        const baseAlpha = isHighlighted ? 0.7 : 0.12;
        const pulse = isHighlighted ? Math.sin(time * 4) * 0.15 + 0.15 : 0;

        ctx.beginPath();
        ctx.moveTo(fromNode.x, fromNode.y);
        // Curved edges
        const mx = (fromNode.x + toNode.x) / 2 + (fromNode.y - toNode.y) * 0.1;
        const my = (fromNode.y + toNode.y) / 2 + (toNode.x - fromNode.x) * 0.1;
        ctx.quadraticCurveTo(mx, my, toNode.x, toNode.y);

        const gradient = ctx.createLinearGradient(fromNode.x, fromNode.y, toNode.x, toNode.y);
        gradient.addColorStop(0, fromNode.color + Math.round((baseAlpha + pulse) * 255).toString(16).padStart(2, "0"));
        gradient.addColorStop(1, toNode.color + Math.round((baseAlpha + pulse) * 255).toString(16).padStart(2, "0"));
        ctx.strokeStyle = gradient;
        ctx.lineWidth = isHighlighted ? 3 : 1.5;
        ctx.stroke();

        // Animated particles on highlighted edges
        if (isHighlighted) {
          const t = (time * 2 + rel.strength) % 1;
          const px = (1 - t) * (1 - t) * fromNode.x + 2 * (1 - t) * t * mx + t * t * toNode.x;
          const py = (1 - t) * (1 - t) * fromNode.y + 2 * (1 - t) * t * my + t * t * toNode.y;
          ctx.beginPath();
          ctx.arc(px, py, 3, 0, Math.PI * 2);
          ctx.fillStyle = "#fff";
          ctx.fill();
        }
      });

      // Draw nodes
      nodes.forEach((node) => {
        const isHighlighted = highlightedEntities && highlightedEntities.includes(node.id);
        const isHovered = hoveredRef.current === node.id;
        const isDimmed = highlightedEntities && highlightedEntities.length > 0 && !isHighlighted;
        const isFiltered = activeFilter && node.domain !== activeFilter && !RELATIONSHIPS.some(
          r => r.domain.includes(activeFilter) && (r.from === node.id || r.to === node.id)
        );

        const alpha = isFiltered ? 0.15 : isDimmed ? 0.3 : 1;
        const r = isHighlighted || isHovered ? node.r * 1.4 : node.r;
        const pulseR = isHighlighted ? Math.sin(time * 3) * 3 : 0;

        // Glow
        if ((isHighlighted || isHovered) && !isFiltered) {
          ctx.beginPath();
          ctx.arc(node.x, node.y, r + 12 + pulseR, 0, Math.PI * 2);
          const grd = ctx.createRadialGradient(node.x, node.y, r, node.x, node.y, r + 12 + pulseR);
          grd.addColorStop(0, node.glow);
          grd.addColorStop(1, "rgba(0,0,0,0)");
          ctx.fillStyle = grd;
          ctx.fill();
        }

        // Node circle
        ctx.beginPath();
        ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
        ctx.fillStyle = node.color + Math.round(alpha * 255 * 0.2).toString(16).padStart(2, "0");
        ctx.fill();
        ctx.strokeStyle = node.color + Math.round(alpha * 255).toString(16).padStart(2, "0");
        ctx.lineWidth = isHighlighted ? 2.5 : 1.5;
        ctx.stroke();

        // Label
        ctx.font = `${isHighlighted ? "bold " : ""}${isHovered ? 17 : 14}px 'IBM Plex Sans', sans-serif`;
        ctx.fillStyle = `rgba(255,255,255,${alpha * (isHighlighted ? 1 : 0.75)})`;
        ctx.textAlign = "center";
        ctx.fillText(node.label, node.x, node.y + r + 18);

        // Spring physics
        node.x += (node.targetX - node.x) * 0.02;
        node.y += (node.targetY - node.y) * 0.02;
        node.x += Math.sin(time + node.targetX * 0.01) * 0.3;
        node.y += Math.cos(time + node.targetY * 0.01) * 0.3;
      });

      animRef.current = requestAnimationFrame(draw);
    }

    draw();
    return () => cancelAnimationFrame(animRef.current);
  }, [entities, highlightedEntities, activeFilter]);

  const handleMouseMove = useCallback((e) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left) * 2;
    const y = (e.clientY - rect.top) * 2;
    const nodes = nodesRef.current;
    let found = null;
    for (const node of nodes) {
      const dx = node.x - x;
      const dy = node.y - y;
      if (Math.sqrt(dx * dx + dy * dy) < node.r * 1.5) {
        found = node.id;
        break;
      }
    }
    hoveredRef.current = found;
    setHovered(found);
    canvas.style.cursor = found ? "pointer" : "default";
  }, []);

  const handleClick = useCallback((e) => {
    if (hoveredRef.current && onNodeClick) {
      const node = nodesRef.current.find((n) => n.id === hoveredRef.current);
      if (node) onNodeClick(node);
    }
  }, [onNodeClick]);

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      <canvas
        ref={canvasRef}
        onMouseMove={handleMouseMove}
        onClick={handleClick}
        style={{ display: "block", width: "100%", height: "100%" }}
      />
      {hovered && (() => {
        const node = nodesRef.current.find((n) => n.id === hovered);
        if (!node) return null;
        const canvas = canvasRef.current;
        const rect = canvas.getBoundingClientRect();
        const sx = node.x / 2;
        const sy = node.y / 2;
        return (
          <div style={{
            position: "absolute", left: sx + 20, top: sy - 20,
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

// ── Typewriter Effect ────────────────────────────────────────────────
function Typewriter({ text, speed = 12, onDone }) {
  const [displayed, setDisplayed] = useState("");
  const idx = useRef(0);

  useEffect(() => {
    idx.current = 0;
    setDisplayed("");
    const interval = setInterval(() => {
      idx.current++;
      if (idx.current >= text.length) {
        setDisplayed(text);
        clearInterval(interval);
        onDone && onDone();
      } else {
        setDisplayed(text.slice(0, idx.current));
      }
    }, speed);
    return () => clearInterval(interval);
  }, [text, speed]);

  return <span>{displayed}<span style={{ opacity: displayed.length < text.length ? 1 : 0, color: "#FCD34D" }}>▌</span></span>;
}

// ── Main App ─────────────────────────────────────────────────────────
export default function TrustGraphRetailDemo() {
  const [activeTab, setActiveTab] = useState("graph");
  const [activeFilter, setActiveFilter] = useState(null);
  const [selectedQuery, setSelectedQuery] = useState(null);
  const [queryPhase, setQueryPhase] = useState("idle"); // idle, thinking, answering, done
  const [thinkingStep, setThinkingStep] = useState(0);
  const [selectedNode, setSelectedNode] = useState(null);
  const [showOntology, setShowOntology] = useState(false);

  const runQuery = (idx) => {
    setSelectedQuery(idx);
    setQueryPhase("thinking");
    setThinkingStep(0);
    const q = DEMO_QUERIES[idx];
    let step = 0;
    const interval = setInterval(() => {
      step++;
      if (step >= q.thinking.length) {
        clearInterval(interval);
        setTimeout(() => setQueryPhase("answering"), 400);
      }
      setThinkingStep(step);
    }, 800);
  };

  const highlightedEntities = selectedQuery !== null && queryPhase !== "idle"
    ? DEMO_QUERIES[selectedQuery].entities
    : selectedNode
    ? [selectedNode.id, ...RELATIONSHIPS.filter(r => r.from === selectedNode.id || r.to === selectedNode.id).map(r => r.from === selectedNode.id ? r.to : r.from)]
    : [];

  return (
    <div style={{
      width: "100%", minHeight: "100vh", background: "#0A0A0F",
      fontFamily: "'IBM Plex Sans', -apple-system, sans-serif",
      color: "#E5E5E5", overflow: "hidden",
    }}>
      {/* ── Header ────────────────────────────────────────── */}
      <div style={{
        borderBottom: "1px solid rgba(255,255,255,0.06)",
        padding: "16px 28px", display: "flex", alignItems: "center", justifyContent: "space-between",
        background: "linear-gradient(180deg, rgba(15,15,22,1) 0%, rgba(10,10,15,1) 100%)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 8,
            background: "linear-gradient(135deg, #6EE7B7 0%, #93C5FD 50%, #F9A8D4 100%)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 18, fontWeight: 900, color: "#0A0A0F",
          }}>TG</div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 16, letterSpacing: "-0.02em", color: "#fff" }}>
              TrustGraph
            </div>
            <div style={{ fontSize: 11, color: "#666", fontFamily: "'IBM Plex Mono', monospace", letterSpacing: "0.05em" }}>
              RETAIL INTELLIGENCE PLATFORM
            </div>
          </div>
        </div>
        <div style={{ display: "flex", gap: 6, fontFamily: "'IBM Plex Mono', monospace", fontSize: 12 }}>
          {["graph", "query", "ontology"].map((tab) => (
            <button key={tab} onClick={() => { setActiveTab(tab); if (tab !== "query") { setSelectedQuery(null); setQueryPhase("idle"); } }}
              style={{
                padding: "7px 16px", borderRadius: 6, border: "none", cursor: "pointer",
                background: activeTab === tab ? "rgba(255,255,255,0.1)" : "transparent",
                color: activeTab === tab ? "#fff" : "#666",
                fontFamily: "'IBM Plex Mono', monospace", fontSize: 12, fontWeight: activeTab === tab ? 600 : 400,
                transition: "all 0.2s",
              }}>
              {tab === "graph" ? "◈ Context Graph" : tab === "query" ? "⚡ Agent Query" : "◇ Ontology"}
            </button>
          ))}
        </div>
      </div>

      {/* ── Domain Filter Bar ──────────────────────────────── */}
      {activeTab === "graph" && (
        <div style={{
          padding: "12px 28px", display: "flex", gap: 8, alignItems: "center",
          borderBottom: "1px solid rgba(255,255,255,0.04)",
        }}>
          <span style={{ fontSize: 11, color: "#555", fontFamily: "'IBM Plex Mono', monospace", marginRight: 8 }}>FILTER:</span>
          <button onClick={() => setActiveFilter(null)}
            style={{
              padding: "5px 12px", borderRadius: 20, border: `1px solid ${!activeFilter ? '#fff' : 'rgba(255,255,255,0.1)'}`,
              background: !activeFilter ? "rgba(255,255,255,0.08)" : "transparent",
              color: !activeFilter ? "#fff" : "#777", fontSize: 11, cursor: "pointer",
              fontFamily: "'IBM Plex Mono', monospace",
            }}>All</button>
          {Object.entries(ONTOLOGY).map(([key, data]) => (
            <button key={key} onClick={() => setActiveFilter(activeFilter === key ? null : key)}
              style={{
                padding: "5px 12px", borderRadius: 20,
                border: `1px solid ${activeFilter === key ? data.color + '88' : 'rgba(255,255,255,0.1)'}`,
                background: activeFilter === key ? data.color + "15" : "transparent",
                color: activeFilter === key ? data.color : "#777",
                fontSize: 11, cursor: "pointer", fontFamily: "'IBM Plex Mono', monospace",
              }}>
              {data.icon} {data.label}
            </button>
          ))}
          <div style={{ marginLeft: "auto", fontSize: 11, color: "#444", fontFamily: "'IBM Plex Mono', monospace" }}>
            {getAllEntities().length} entities · {RELATIONSHIPS.length} relationships
          </div>
        </div>
      )}

      {/* ── Main Content ──────────────────────────────────── */}
      <div style={{ display: "flex", height: "calc(100vh - 110px)" }}>

        {/* ── Graph View ──────────────────────────────────── */}
        {activeTab === "graph" && (
          <>
            <div style={{ flex: 1, position: "relative" }}>
              <GraphCanvas
                highlightedEntities={highlightedEntities}
                onNodeClick={(node) => setSelectedNode(selectedNode?.id === node.id ? null : node)}
                activeFilter={activeFilter}
              />
            </div>
            {/* Side panel for selected node */}
            {selectedNode && (
              <div style={{
                width: 320, borderLeft: "1px solid rgba(255,255,255,0.06)",
                background: "rgba(12,12,18,0.95)", padding: 24, overflowY: "auto",
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
                  <div style={{ color: ONTOLOGY[selectedNode.domain].color, fontSize: 11, fontFamily: "'IBM Plex Mono', monospace", fontWeight: 600 }}>
                    {ONTOLOGY[selectedNode.domain].label.toUpperCase()} ENTITY
                  </div>
                  <button onClick={() => setSelectedNode(null)} style={{ background: "none", border: "none", color: "#666", cursor: "pointer", fontSize: 18 }}>×</button>
                </div>
                <div style={{ fontSize: 20, fontWeight: 700, color: "#fff", marginBottom: 6 }}>
                  {selectedNode.icon} {selectedNode.label}
                </div>
                <div style={{ marginTop: 20 }}>
                  <div style={{ fontSize: 10, color: "#555", fontFamily: "'IBM Plex Mono', monospace", marginBottom: 10, letterSpacing: "0.1em" }}>PROPERTIES</div>
                  {Object.entries(selectedNode.props || {}).map(([k, v]) => (
                    <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                      <span style={{ fontSize: 12, color: "#888" }}>{k}</span>
                      <span style={{ fontSize: 12, color: "#ddd", fontFamily: "'IBM Plex Mono', monospace" }}>{String(v)}</span>
                    </div>
                  ))}
                </div>
                <div style={{ marginTop: 24 }}>
                  <div style={{ fontSize: 10, color: "#555", fontFamily: "'IBM Plex Mono', monospace", marginBottom: 10, letterSpacing: "0.1em" }}>RELATIONSHIPS</div>
                  {RELATIONSHIPS.filter(r => r.from === selectedNode.id || r.to === selectedNode.id).map((r, i) => {
                    const otherId = r.from === selectedNode.id ? r.to : r.from;
                    const other = getAllEntities().find(e => e.id === otherId);
                    const direction = r.from === selectedNode.id ? "→" : "←";
                    return (
                      <div key={i} style={{
                        padding: "8px 10px", marginBottom: 4, borderRadius: 6,
                        background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.04)",
                        cursor: "pointer",
                      }} onClick={() => { const n = getAllEntities().find(e => e.id === otherId); if (n) setSelectedNode(n); }}>
                        <div style={{ fontSize: 11, color: "#aaa" }}>
                          <span style={{ color: other?.color || "#888" }}>{direction} {other?.label}</span>
                        </div>
                        <div style={{ fontSize: 10, color: "#666", fontFamily: "'IBM Plex Mono', monospace", marginTop: 2 }}>
                          {r.predicate.replace(/_/g, " ")} · strength: {r.strength}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </>
        )}

        {/* ── Agent Query View ────────────────────────────── */}
        {activeTab === "query" && (
          <div style={{ flex: 1, display: "flex" }}>
            <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
              {/* Query selector */}
              <div style={{ padding: "20px 28px", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                <div style={{ fontSize: 10, color: "#555", fontFamily: "'IBM Plex Mono', monospace", marginBottom: 12, letterSpacing: "0.1em" }}>
                  SELECT A QUERY TO SEE GRAPH-POWERED AGENT INTELLIGENCE
                </div>
                {DEMO_QUERIES.map((dq, idx) => (
                  <button key={idx} onClick={() => runQuery(idx)}
                    style={{
                      display: "block", width: "100%", textAlign: "left",
                      padding: "12px 16px", marginBottom: 8, borderRadius: 8,
                      border: `1px solid ${selectedQuery === idx ? '#FCD34D33' : 'rgba(255,255,255,0.06)'}`,
                      background: selectedQuery === idx ? "rgba(252,211,77,0.05)" : "rgba(255,255,255,0.02)",
                      color: selectedQuery === idx ? "#FCD34D" : "#bbb",
                      cursor: "pointer", fontSize: 13, lineHeight: 1.5,
                      fontFamily: "'IBM Plex Sans', sans-serif",
                      transition: "all 0.2s",
                    }}>
                    <span style={{ color: "#FCD34D88", fontFamily: "'IBM Plex Mono', monospace", fontSize: 11 }}>⚡ QUERY {idx + 1}</span><br />
                    {dq.q}
                  </button>
                ))}
              </div>

              {/* Response area */}
              {selectedQuery !== null && (
                <div style={{ flex: 1, padding: "24px 28px", overflowY: "auto" }}>
                  {/* Graph traversal steps */}
                  {(queryPhase === "thinking" || queryPhase === "answering" || queryPhase === "done") && (
                    <div style={{ marginBottom: 24 }}>
                      <div style={{ fontSize: 10, color: "#FCD34D88", fontFamily: "'IBM Plex Mono', monospace", marginBottom: 12, letterSpacing: "0.1em" }}>
                        ◈ GRAPH TRAVERSAL
                      </div>
                      {DEMO_QUERIES[selectedQuery].thinking.map((step, i) => (
                        <div key={i} style={{
                          padding: "8px 12px", marginBottom: 4, borderRadius: 6,
                          background: i < thinkingStep ? "rgba(252,211,77,0.04)" : "rgba(255,255,255,0.01)",
                          borderLeft: `2px solid ${i < thinkingStep ? '#FCD34D44' : 'rgba(255,255,255,0.04)'}`,
                          opacity: i < thinkingStep ? 1 : 0.3,
                          transition: "all 0.4s",
                          fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: "#aaa",
                        }}>
                          {i < thinkingStep && <span style={{ color: "#6EE7B7", marginRight: 8 }}>✓</span>}
                          {step}
                        </div>
                      ))}
                      {queryPhase === "thinking" && (
                        <div style={{ marginTop: 8, fontSize: 11, color: "#FCD34D66", fontFamily: "'IBM Plex Mono', monospace" }}>
                          Traversing graph...
                        </div>
                      )}
                    </div>
                  )}

                  {/* Answer */}
                  {(queryPhase === "answering" || queryPhase === "done") && (
                    <div style={{
                      padding: 20, borderRadius: 10,
                      background: "linear-gradient(135deg, rgba(252,211,77,0.04) 0%, rgba(110,231,183,0.04) 100%)",
                      border: "1px solid rgba(252,211,77,0.12)",
                    }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12, alignItems: "center" }}>
                        <div style={{ fontSize: 10, color: "#FCD34D88", fontFamily: "'IBM Plex Mono', monospace", letterSpacing: "0.1em" }}>
                          AGENT RESPONSE
                        </div>
                        <div style={{ fontSize: 10, color: "#555", fontFamily: "'IBM Plex Mono', monospace" }}>
                          {DEMO_QUERIES[selectedQuery].triples} triples traversed · {DEMO_QUERIES[selectedQuery].entities.length} entities resolved
                        </div>
                      </div>
                      <div style={{ fontSize: 14, lineHeight: 1.7, color: "#ddd" }}>
                        <Typewriter
                          text={DEMO_QUERIES[selectedQuery].answer}
                          speed={10}
                          onDone={() => setQueryPhase("done")}
                        />
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Graph visualization alongside query */}
            <div style={{ width: "45%", borderLeft: "1px solid rgba(255,255,255,0.06)" }}>
              <GraphCanvas highlightedEntities={highlightedEntities} onNodeClick={() => {}} activeFilter={null} />
            </div>
          </div>
        )}

        {/* ── Ontology View ──────────────────────────────── */}
        {activeTab === "ontology" && (
          <div style={{ flex: 1, padding: "28px", overflowY: "auto" }}>
            <div style={{ maxWidth: 900, margin: "0 auto" }}>
              <div style={{ fontSize: 10, color: "#555", fontFamily: "'IBM Plex Mono', monospace", letterSpacing: "0.1em", marginBottom: 24 }}>
                ONTOLOGY SCHEMA · RETAIL INTELLIGENCE DOMAIN
              </div>

              {/* Ontology class cards */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 32 }}>
                {Object.entries(ONTOLOGY).map(([key, data]) => (
                  <div key={key} style={{
                    padding: 24, borderRadius: 12,
                    background: "rgba(255,255,255,0.02)",
                    border: `1px solid ${data.color}22`,
                  }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
                      <span style={{ fontSize: 24 }}>{data.icon}</span>
                      <div>
                        <div style={{ fontWeight: 700, fontSize: 18, color: data.color }}>{data.label}</div>
                        <div style={{ fontSize: 11, color: "#666", fontFamily: "'IBM Plex Mono', monospace" }}>owl:Class</div>
                      </div>
                    </div>
                    <div style={{ fontSize: 12, color: "#888", lineHeight: 1.5, marginBottom: 14 }}>{data.description}</div>
                    <div style={{ fontSize: 10, color: "#555", fontFamily: "'IBM Plex Mono', monospace", marginBottom: 8, letterSpacing: "0.05em" }}>PROPERTIES</div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                      {data.properties.map((p) => (
                        <span key={p} style={{
                          padding: "3px 8px", borderRadius: 4, fontSize: 10,
                          background: data.color + "10", color: data.color + "cc",
                          fontFamily: "'IBM Plex Mono', monospace",
                          border: `1px solid ${data.color}22`,
                        }}>{p}</span>
                      ))}
                    </div>
                    <div style={{ fontSize: 10, color: "#555", fontFamily: "'IBM Plex Mono', monospace", marginTop: 14, marginBottom: 8, letterSpacing: "0.05em" }}>
                      INSTANCES ({data.subclasses.length})
                    </div>
                    {data.subclasses.map((sc) => (
                      <div key={sc.id} style={{
                        padding: "6px 10px", marginBottom: 3, borderRadius: 4,
                        background: "rgba(255,255,255,0.02)", fontSize: 11, color: "#aaa",
                        display: "flex", justifyContent: "space-between",
                      }}>
                        <span>{sc.label}</span>
                        <span style={{ color: "#555", fontFamily: "'IBM Plex Mono', monospace", fontSize: 10 }}>{sc.id}</span>
                      </div>
                    ))}
                  </div>
                ))}
              </div>

              {/* Relationship predicates */}
              <div style={{
                padding: 24, borderRadius: 12,
                background: "rgba(255,255,255,0.02)",
                border: "1px solid rgba(255,255,255,0.06)",
              }}>
                <div style={{ fontSize: 10, color: "#555", fontFamily: "'IBM Plex Mono', monospace", letterSpacing: "0.1em", marginBottom: 16 }}>
                  RELATIONSHIP PREDICATES
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
                  {[...new Set(RELATIONSHIPS.map(r => r.predicate))].map((pred) => {
                    const sample = RELATIONSHIPS.find(r => r.predicate === pred);
                    const fromDomain = sample.domain[0];
                    const toDomain = sample.domain[1];
                    return (
                      <div key={pred} style={{
                        padding: "10px 12px", borderRadius: 6,
                        background: "rgba(255,255,255,0.02)",
                        border: "1px solid rgba(255,255,255,0.04)",
                      }}>
                        <div style={{ fontSize: 12, color: "#ccc", fontFamily: "'IBM Plex Mono', monospace", marginBottom: 4 }}>
                          {pred.replace(/_/g, " ")}
                        </div>
                        <div style={{ fontSize: 10, color: "#555" }}>
                          <span style={{ color: ONTOLOGY[fromDomain].color }}>{ONTOLOGY[fromDomain].label}</span>
                          {" → "}
                          <span style={{ color: ONTOLOGY[toDomain].color }}>{ONTOLOGY[toDomain].label}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Triple count summary */}
              <div style={{
                marginTop: 20, padding: "16px 24px", borderRadius: 10,
                background: "linear-gradient(135deg, rgba(110,231,183,0.04) 0%, rgba(147,197,253,0.04) 50%, rgba(249,168,212,0.04) 100%)",
                border: "1px solid rgba(255,255,255,0.06)",
                display: "flex", justifyContent: "space-around",
                fontFamily: "'IBM Plex Mono', monospace",
              }}>
                {[
                  { label: "Classes", value: 4 },
                  { label: "Instances", value: getAllEntities().length },
                  { label: "Predicates", value: [...new Set(RELATIONSHIPS.map(r => r.predicate))].length },
                  { label: "Triples", value: RELATIONSHIPS.length },
                ].map((s) => (
                  <div key={s.label} style={{ textAlign: "center" }}>
                    <div style={{ fontSize: 24, fontWeight: 700, color: "#fff" }}>{s.value}</div>
                    <div style={{ fontSize: 10, color: "#666", letterSpacing: "0.05em" }}>{s.label.toUpperCase()}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── Bottom Status Bar ──────────────────────────────── */}
      <div style={{
        position: "fixed", bottom: 0, left: 0, right: 0,
        padding: "8px 28px", borderTop: "1px solid rgba(255,255,255,0.04)",
        background: "rgba(10,10,15,0.95)", backdropFilter: "blur(8px)",
        display: "flex", justifyContent: "space-between", alignItems: "center",
        fontFamily: "'IBM Plex Mono', monospace", fontSize: 10, color: "#444",
      }}>
        <div style={{ display: "flex", gap: 20 }}>
          <span>◈ Ontology: Consumer × Agent × Retail × Brand</span>
          <span>⬡ GraphRAG: Active</span>
          <span>⚡ Agent Orchestration: Online</span>
        </div>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <span style={{ color: "#6EE7B7" }}>●</span> Context Graph Connected
          <span style={{ color: "#888" }}>|</span>
          <span>trustgraph.ai</span>
        </div>
      </div>
    </div>
  );
}
