import { text, surface, border, palette } from "../../theme";

interface SearchInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  placeholder?: string;
  buttonText?: string;
  isLoading?: boolean;
  buttonColor?: string;
  disabled?: boolean;
}

export function SearchInput({
  value,
  onChange,
  onSubmit,
  placeholder = "Search...",
  buttonText = "Search",
  isLoading = false,
  buttonColor = palette.blue,
  disabled = false,
}: SearchInputProps) {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSubmit();
    }
  };

  const isDisabled = disabled || isLoading || !value.trim();

  return (
    <div style={{ display: "flex", gap: 8 }}>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={isLoading}
        style={{
          flex: 1,
          padding: "12px 16px",
          borderRadius: 8,
          border: `1px solid ${border.medium}`,
          background: surface.card,
          color: text.primary,
          fontSize: 14,
          fontFamily: "'IBM Plex Sans', sans-serif",
          outline: "none",
        }}
      />
      <button
        onClick={onSubmit}
        disabled={isDisabled}
        style={{
          padding: "12px 20px",
          borderRadius: 8,
          border: `1px solid ${buttonColor}44`,
          background: isDisabled ? surface.card : `${buttonColor}1a`,
          color: isDisabled ? text.disabled : buttonColor,
          cursor: isDisabled ? "not-allowed" : "pointer",
          fontSize: 13,
          fontWeight: 600,
          fontFamily: "'IBM Plex Mono', monospace",
        }}
      >
        {isLoading ? "..." : buttonText}
      </button>
    </div>
  );
}
