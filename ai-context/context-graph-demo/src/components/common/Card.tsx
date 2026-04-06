import { surface, border } from "../../theme";

interface CardProps {
  children: React.ReactNode;
  padding?: number | string;
  borderRadius?: number;
  borderColor?: string;
  onClick?: () => void;
  style?: React.CSSProperties;
}

export function Card({
  children,
  padding = 24,
  borderRadius = 12,
  borderColor = border.subtle,
  onClick,
  style,
}: CardProps) {
  return (
    <div
      onClick={onClick}
      style={{
        padding,
        borderRadius,
        background: surface.card,
        border: `1px solid ${borderColor}`,
        cursor: onClick ? "pointer" : undefined,
        ...style,
      }}
    >
      {children}
    </div>
  );
}
