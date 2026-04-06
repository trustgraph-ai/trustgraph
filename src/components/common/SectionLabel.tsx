import { text } from "../../theme";

interface SectionLabelProps {
  children: React.ReactNode;
  marginBottom?: number;
  marginTop?: number;
}

export function SectionLabel({ children, marginBottom = 10, marginTop }: SectionLabelProps) {
  return (
    <div style={{
      fontSize: 10,
      color: text.disabled,
      fontFamily: "'IBM Plex Mono', monospace",
      letterSpacing: "0.1em",
      marginBottom,
      marginTop,
    }}>
      {children}
    </div>
  );
}
