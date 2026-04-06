// Primary palette (migrated from useGraphData.ts)
export const palette = {
  emerald: "#6EE7B7",
  pink: "#F9A8D4",
  blue: "#93C5FD",
  amber: "#FCD34D",
  purple: "#C4B5FD",
  rose: "#FDA4AF",
  cyan: "#67E8F9",
  red: "#FCA5A5",
  orange: "#F97316",
};

// Semantic colors
export const semantic = {
  success: palette.emerald,
  error: "#f66",
  warning: palette.orange,
  info: palette.blue,
  thinking: palette.blue,
  observation: palette.purple,
  answer: palette.emerald,
  user: palette.amber,
};

// Text colors (dark theme)
export const text = {
  primary: "#ddd",
  secondary: "#bbb",
  muted: "#aaa",
  subtle: "#888",
  faint: "#666",
  disabled: "#555",
  hint: "#444",
};

// Surface/background colors
export const surface = {
  base: "#0A0A0F",
  overlay: "rgba(15,15,20,0.95)",
  overlayLight: "rgba(15,15,20,0.8)",
  card: "rgba(255,255,255,0.02)",
  cardHover: "rgba(255,255,255,0.04)",
};

// Border colors
export const border = {
  subtle: "rgba(255,255,255,0.04)",
  default: "rgba(255,255,255,0.06)",
  medium: "rgba(255,255,255,0.1)",
  grid: "rgba(255,255,255,0.015)",
};

// Helper: Generate glow color from hex
export function withGlow(hex: string, opacity = 0.4): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${opacity})`;
}

// Domain color palette (array for cycling)
export const domainColors = [
  { color: palette.emerald, glow: withGlow(palette.emerald) },
  { color: palette.pink, glow: withGlow(palette.pink) },
  { color: palette.blue, glow: withGlow(palette.blue) },
  { color: palette.amber, glow: withGlow(palette.amber) },
  { color: palette.purple, glow: withGlow(palette.purple) },
  { color: palette.rose, glow: withGlow(palette.rose) },
  { color: palette.cyan, glow: withGlow(palette.cyan) },
  { color: palette.red, glow: withGlow(palette.red) },
];
