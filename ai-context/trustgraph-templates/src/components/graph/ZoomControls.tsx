import { surface, border, text } from "../../theme";

interface ZoomControlsProps {
  zoom: number;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onReset: () => void;
}

export function ZoomControls({ zoom, onZoomIn, onZoomOut, onReset }: ZoomControlsProps) {
  const buttonStyle: React.CSSProperties = {
    width: 28,
    height: 28,
    border: "none",
    borderRadius: 4,
    background: border.medium,
    color: text.subtle,
    cursor: "pointer",
    fontSize: 16,
    fontWeight: "bold",
  };

  return (
    <>
      {/* Zoom controls */}
      <div style={{
        position: "absolute",
        bottom: 16,
        right: 16,
        display: "flex",
        flexDirection: "column",
        gap: 4,
        background: surface.overlayLight,
        borderRadius: 8,
        padding: 4,
        border: `1px solid ${border.medium}`,
      }}>
        <button
          onClick={onZoomIn}
          style={buttonStyle}
          title="Zoom in"
        >+</button>
        <button
          onClick={onZoomOut}
          style={buttonStyle}
          title="Zoom out"
        >−</button>
        <button
          onClick={onReset}
          style={{ ...buttonStyle, fontSize: 10 }}
          title="Reset view"
        >⟲</button>
      </div>

      {/* Zoom indicator */}
      {zoom !== 1 && (
        <div style={{
          position: "absolute",
          bottom: 16,
          left: 16,
          fontSize: 11,
          fontFamily: "'IBM Plex Mono', monospace",
          color: text.faint,
          background: surface.overlayLight,
          padding: "4px 8px",
          borderRadius: 4,
        }}>
          {Math.round(zoom * 100)}%
        </div>
      )}
    </>
  );
}
