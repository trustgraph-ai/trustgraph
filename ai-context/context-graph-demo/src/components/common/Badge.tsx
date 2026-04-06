interface BadgeProps {
  children: React.ReactNode;
  color: string;
  size?: "small" | "medium";
  selected?: boolean;
  onClick?: () => void;
}

export function Badge({
  children,
  color,
  size = "medium",
  selected = false,
  onClick,
}: BadgeProps) {
  const isSmall = size === "small";

  return (
    <button
      onClick={onClick}
      style={{
        padding: isSmall ? "3px 8px" : "6px 12px",
        borderRadius: isSmall ? 4 : 6,
        border: `1px solid ${selected ? color : color + (isSmall ? "22" : "44")}`,
        background: selected ? `${color}35` : `${color}${isSmall ? "10" : "15"}`,
        color: isSmall ? color + "cc" : color,
        cursor: onClick ? "pointer" : "default",
        fontSize: isSmall ? 10 : 11,
        fontFamily: "'IBM Plex Mono', monospace",
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        boxShadow: selected ? `0 0 8px ${color}44` : "none",
      }}
    >
      {children}
    </button>
  );
}
