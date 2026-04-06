import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import ChatMessage from "../ChatMessage";

// Helper function to filter out Chakra UI props
const filterChakraProps = (props: Record<string, unknown>) => {
  const chakraProps = [
    "alignItems",
    "justifyContent",
    "direction",
    "gap",
    "p",
    "px",
    "py",
    "pt",
    "pb",
    "pl",
    "pr",
    "m",
    "mx",
    "my",
    "mt",
    "mb",
    "ml",
    "mr",
    "w",
    "h",
    "maxW",
    "maxH",
    "minW",
    "minH",
    "bg",
    "color",
    "borderRadius",
    "borderWidth",
    "borderColor",
    "borderStyle",
    "boxShadow",
    "display",
    "position",
    "top",
    "right",
    "bottom",
    "left",
    "zIndex",
    "overflow",
    "textAlign",
    "fontSize",
    "fontWeight",
    "lineHeight",
    "letterSpacing",
    "textTransform",
    "textDecoration",
    "opacity",
    "visibility",
    "cursor",
    "pointerEvents",
    "userSelect",
    "resize",
    "outline",
    "transform",
    "transformOrigin",
    "transition",
    "animation",
    "colorPalette",
    "variant",
    "size",
    "loading",
    "disabled",
    "checked",
    "selected",
    "active",
    "focus",
    "hover",
    "flexDirection",
    "flexWrap",
    "flex",
    "flexGrow",
    "flexShrink",
    "flexBasis",
    "alignSelf",
    "justifySelf",
    "order",
    "gridColumn",
    "gridRow",
    "gridArea",
    "gridTemplateColumns",
    "gridTemplateRows",
    "gridGap",
    "rowGap",
    "columnGap",
    "placeItems",
    "placeContent",
    "placeSelf",
    "area",
    "colSpan",
    "rowSpan",
    "start",
    "end",
  ];
  const filtered = { ...props };
  chakraProps.forEach((prop) => delete filtered[prop]);
  return filtered;
};

// Mock Chakra UI components
vi.mock("@chakra-ui/react", () => ({
  Box: ({
    children,
    ...props
  }: React.PropsWithChildren<Record<string, unknown>>) => (
    <div data-testid="box" {...filterChakraProps(props)}>
      {children}
    </div>
  ),
  Flex: ({
    children,
    ...props
  }: React.PropsWithChildren<Record<string, unknown>>) => (
    <div data-testid="flex" {...filterChakraProps(props)}>
      {children}
    </div>
  ),
  Text: ({
    children,
    ...props
  }: React.PropsWithChildren<Record<string, unknown>>) => (
    <p data-testid="text" {...filterChakraProps(props)}>
      {children}
    </p>
  ),
  Avatar: {
    Root: ({
      children,
      ...props
    }: React.PropsWithChildren<Record<string, unknown>>) => (
      <div data-testid="avatar-root" {...filterChakraProps(props)}>
        {children}
      </div>
    ),
    Fallback: ({
      name,
      ...props
    }: { name?: string } & Record<string, unknown>) => (
      <div data-testid="avatar-fallback" {...filterChakraProps(props)}>
        {name}
      </div>
    ),
  },
  Badge: ({
    children,
    ...props
  }: React.PropsWithChildren<Record<string, unknown>>) => (
    <span data-testid="badge" {...filterChakraProps(props)}>
      {children}
    </span>
  ),
}));

// Mock react-markdown-it
vi.mock("react-markdown-it", () => ({
  default: ({ children }: React.PropsWithChildren) => (
    <div data-testid="markdown">{children}</div>
  ),
}));

// Mock lucide-react icons
vi.mock("lucide-react", () => ({
  Brain: () => <div data-testid="brain-icon">Brain</div>,
  Eye: () => <div data-testid="eye-icon">Eye</div>,
  CheckCircle: () => <div data-testid="check-circle-icon">CheckCircle</div>,
}));

describe("ChatMessage", () => {
  it("should render user message with correct styling", () => {
    const message = {
      role: "human",
      text: "Hello, how are you?",
      type: "normal",
    };

    render(<ChatMessage message={message} />);

    expect(screen.getByTestId("markdown")).toHaveTextContent(
      "Hello, how are you?",
    );
    expect(screen.getByTestId("avatar-fallback")).toHaveTextContent("User");
  });

  it("should render AI message with correct styling", () => {
    const message = {
      role: "ai",
      text: "I am doing well, thank you!",
      type: "normal",
    };

    render(<ChatMessage message={message} />);

    expect(screen.getByTestId("markdown")).toHaveTextContent(
      "I am doing well, thank you!",
    );
    expect(screen.getByTestId("avatar-fallback")).toHaveTextContent("Bot");
  });

  it("should render thinking message with correct badge and icon", () => {
    const message = {
      role: "ai",
      text: "Let me think about this...",
      type: "thinking",
    };

    render(<ChatMessage message={message} />);

    expect(screen.getByTestId("brain-icon")).toBeInTheDocument();
    expect(screen.getByTestId("badge")).toHaveTextContent("Thinking");
    expect(screen.getByTestId("markdown")).toHaveTextContent(
      "Let me think about this...",
    );
  });

  it("should render observation message with correct badge and icon", () => {
    const message = {
      role: "ai",
      text: "I observe that...",
      type: "observation",
    };

    render(<ChatMessage message={message} />);

    expect(screen.getByTestId("eye-icon")).toBeInTheDocument();
    expect(screen.getByTestId("badge")).toHaveTextContent("Observation");
    expect(screen.getByTestId("markdown")).toHaveTextContent(
      "I observe that...",
    );
  });

  it("should render answer message with correct badge and icon", () => {
    const message = {
      role: "ai",
      text: "The answer is 42.",
      type: "answer",
    };

    render(<ChatMessage message={message} />);

    expect(screen.getByTestId("check-circle-icon")).toBeInTheDocument();
    expect(screen.getByTestId("badge")).toHaveTextContent("Answer");
    expect(screen.getByTestId("markdown")).toHaveTextContent(
      "The answer is 42.",
    );
  });

  it("should handle message without type (defaults to normal)", () => {
    const message = {
      role: "ai",
      text: "Regular message",
    };

    render(<ChatMessage message={message} />);

    expect(screen.getByTestId("markdown")).toHaveTextContent(
      "Regular message",
    );
    expect(screen.queryByTestId("badge")).not.toBeInTheDocument();
  });

  it("should handle empty message text", () => {
    const message = {
      role: "human",
      text: "",
      type: "normal",
    };

    render(<ChatMessage message={message} />);

    expect(screen.getByTestId("markdown")).toHaveTextContent("");
  });

  it("should handle markdown content", () => {
    const message = {
      role: "ai",
      text: "**Bold text** and *italic text*",
      type: "normal",
    };

    render(<ChatMessage message={message} />);

    expect(screen.getByTestId("markdown")).toHaveTextContent(
      "**Bold text** and *italic text*",
    );
  });

  it("should differentiate between user and AI avatar placement", () => {
    const userMessage = {
      role: "human",
      text: "User message",
      type: "normal",
    };

    const { rerender } = render(<ChatMessage message={userMessage} />);

    expect(screen.getByTestId("avatar-fallback")).toHaveTextContent("User");

    const aiMessage = {
      role: "ai",
      text: "AI message",
      type: "normal",
    };

    rerender(<ChatMessage message={aiMessage} />);

    expect(screen.getByTestId("avatar-fallback")).toHaveTextContent("Bot");
  });

  it("should handle all message types with correct styling", () => {
    const messageTypes = ["normal", "thinking", "observation", "answer"];

    messageTypes.forEach((type) => {
      const message = {
        role: "ai",
        text: `Message of type ${type}`,
        type: type,
      };

      const { unmount } = render(<ChatMessage message={message} />);

      expect(screen.getByTestId("markdown")).toHaveTextContent(
        `Message of type ${type}`,
      );

      if (type !== "normal") {
        expect(screen.getByTestId("badge")).toBeInTheDocument();
      }

      unmount();
    });
  });

  it("should handle unknown message type (falls back to normal)", () => {
    const message = {
      role: "ai",
      text: "Unknown type message",
      type: "unknown",
    };

    render(<ChatMessage message={message} />);

    expect(screen.getByTestId("markdown")).toHaveTextContent(
      "Unknown type message",
    );
    expect(screen.queryByTestId("badge")).not.toBeInTheDocument();
  });
});
