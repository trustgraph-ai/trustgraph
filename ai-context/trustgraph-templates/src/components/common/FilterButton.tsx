import { text, border } from "../../theme";

interface FilterButtonProps {
  label: string;
  icon?: string;
  color?: string;
  isActive: boolean;
  onClick: () => void;
}

export function FilterButton({ label, icon, color, isActive, onClick }: FilterButtonProps) {
  const activeColor = color || "#fff";

  return (
    <button
      onClick={onClick}
      style={{
        padding: "5px 12px",
        borderRadius: 20,
        border: `1px solid ${isActive ? activeColor + "88" : border.medium}`,
        background: isActive ? activeColor + "15" : "transparent",
        color: isActive ? activeColor : text.subtle,
        fontSize: 11,
        cursor: "pointer",
        fontFamily: "'IBM Plex Mono', monospace",
      }}
    >
      {icon && <>{icon} </>}{label}
    </button>
  );
}
