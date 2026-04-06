import { semantic, text, surface, border, withGlow } from "../../theme";

export interface Message {
  role: string;
  text: string;
  type?: string;
}

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "human";
  const messageType = message.type;

  const getTypeStyles = () => {
    switch (messageType) {
      case "thinking":
        return {
          bg: withGlow(semantic.thinking, 0.08),
          border: withGlow(semantic.thinking, 0.2),
          icon: "◈",
          label: "THINKING",
          color: semantic.thinking,
        };
      case "observation":
        return {
          bg: withGlow(semantic.observation, 0.08),
          border: withGlow(semantic.observation, 0.2),
          icon: "◉",
          label: "OBSERVATION",
          color: semantic.observation,
        };
      case "answer":
        return {
          bg: withGlow(semantic.answer, 0.08),
          border: withGlow(semantic.answer, 0.2),
          icon: "✓",
          label: "ANSWER",
          color: semantic.answer,
        };
      default:
        return null;
    }
  };

  const typeStyles = getTypeStyles();

  if (isUser) {
    return (
      <div style={{
        padding: "12px 16px",
        borderRadius: 10,
        background: withGlow(semantic.user, 0.08),
        border: `1px solid ${withGlow(semantic.user, 0.2)}`,
        alignSelf: "flex-end",
        maxWidth: "80%",
      }}>
        <div style={{ fontSize: 10, color: withGlow(semantic.user, 0.53), fontFamily: "'IBM Plex Mono', monospace", marginBottom: 6 }}>
          YOU
        </div>
        <div style={{ fontSize: 14, color: text.primary, lineHeight: 1.5 }}>
          {message.text}
        </div>
      </div>
    );
  }

  return (
    <div style={{
      padding: "12px 16px",
      borderRadius: 10,
      background: typeStyles?.bg || surface.card,
      border: `1px solid ${typeStyles?.border || border.default}`,
      maxWidth: "90%",
    }}>
      {typeStyles && (
        <div style={{
          fontSize: 10,
          color: withGlow(typeStyles.color, 0.53),
          fontFamily: "'IBM Plex Mono', monospace",
          marginBottom: 6,
          display: "flex",
          alignItems: "center",
          gap: 6,
        }}>
          <span style={{ color: typeStyles.color }}>{typeStyles.icon}</span>
          {typeStyles.label}
        </div>
      )}
      <div style={{ fontSize: 13, color: text.secondary, lineHeight: 1.6, whiteSpace: "pre-wrap" }}>
        {message.text}
      </div>
    </div>
  );
}
