import { semantic, text } from "../../theme";

interface LoadingStateProps {
  message?: string;
  variant?: "loading" | "error";
}

export function LoadingState({ message, variant = "loading" }: LoadingStateProps) {
  const isError = variant === "error";
  const defaultMessage = isError ? "Error loading data" : "Loading...";

  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      height: "100%",
      color: isError ? semantic.error : text.faint,
    }}>
      {message || defaultMessage}
    </div>
  );
}
