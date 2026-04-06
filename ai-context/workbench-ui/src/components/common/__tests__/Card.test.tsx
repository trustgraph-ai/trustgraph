import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import Card from "../Card";

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
  Heading: ({
    children,
    ...props
  }: React.PropsWithChildren<Record<string, unknown>>) => (
    <h3 data-testid="heading" {...filterChakraProps(props)}>
      {children}
    </h3>
  ),
  Text: ({
    children,
    ...props
  }: React.PropsWithChildren<Record<string, unknown>>) => (
    <p data-testid="text" {...filterChakraProps(props)}>
      {children}
    </p>
  ),
}));

describe("Card", () => {
  it("should render with title", () => {
    render(<Card title="Test Title" />);

    expect(screen.getByTestId("heading")).toBeInTheDocument();
    expect(screen.getByText("Test Title")).toBeInTheDocument();
  });

  it("should render with description when provided", () => {
    render(<Card title="Test Title" description="Test description" />);

    expect(screen.getByTestId("text")).toBeInTheDocument();
    expect(screen.getByText("Test description")).toBeInTheDocument();
  });

  it("should not render description when not provided", () => {
    render(<Card title="Test Title" />);

    expect(screen.queryByTestId("text")).not.toBeInTheDocument();
  });

  it("should render icon when provided", () => {
    const TestIcon = () => <span data-testid="test-icon">🎯</span>;
    render(<Card title="Test Title" icon={<TestIcon />} />);

    expect(screen.getByTestId("test-icon")).toBeInTheDocument();
    expect(screen.getByText("🎯")).toBeInTheDocument();
  });

  it("should not render icon when not provided", () => {
    render(<Card title="Test Title" />);

    expect(screen.queryByTestId("test-icon")).not.toBeInTheDocument();
  });

  it("should render children when provided", () => {
    render(
      <Card title="Test Title">
        <div data-testid="child-content">Child content</div>
      </Card>,
    );

    expect(screen.getByTestId("child-content")).toBeInTheDocument();
    expect(screen.getByText("Child content")).toBeInTheDocument();
  });

  it("should not render children when not provided", () => {
    render(<Card title="Test Title" />);

    expect(screen.queryByTestId("child-content")).not.toBeInTheDocument();
  });

  it("should render with all props together", () => {
    const TestIcon = () => <span data-testid="test-icon">⭐</span>;
    render(
      <Card
        title="Complete Card"
        description="This is a complete card with all props"
        icon={<TestIcon />}
      >
        <div data-testid="child-content">Children content</div>
      </Card>,
    );

    expect(screen.getByText("Complete Card")).toBeInTheDocument();
    expect(
      screen.getByText("This is a complete card with all props"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("test-icon")).toBeInTheDocument();
    expect(screen.getByTestId("child-content")).toBeInTheDocument();
  });

  it("should handle empty title", () => {
    render(<Card title="" />);

    expect(screen.getByTestId("heading")).toBeInTheDocument();
    expect(screen.getByTestId("heading")).toHaveTextContent("");
  });

  it("should handle empty description", () => {
    render(<Card title="Test Title" description="" />);

    // Empty description should not render the text element
    expect(screen.queryByTestId("text")).not.toBeInTheDocument();
  });

  it("should handle long title", () => {
    const longTitle = "a".repeat(100);
    render(<Card title={longTitle} />);

    expect(screen.getByText(longTitle)).toBeInTheDocument();
  });

  it("should handle long description", () => {
    const longDescription = "b".repeat(500);
    render(<Card title="Test Title" description={longDescription} />);

    expect(screen.getByText(longDescription)).toBeInTheDocument();
  });

  it("should handle special characters in title", () => {
    const specialTitle = "!@#$%^&*()_+{}[]|\\:;\"'<>,.?/~`";
    render(<Card title={specialTitle} />);

    expect(screen.getByText(specialTitle)).toBeInTheDocument();
  });

  it("should handle special characters in description", () => {
    const specialDescription = "!@#$%^&*()_+{}[]|\\:;\"'<>,.?/~`";
    render(<Card title="Test Title" description={specialDescription} />);

    expect(screen.getByText(specialDescription)).toBeInTheDocument();
  });

  it("should handle multiline title", () => {
    const multilineTitle = "Line 1\nLine 2\nLine 3";
    render(<Card title={multilineTitle} />);

    // Check that content is rendered (newlines may be normalized)
    expect(screen.getByTestId("heading")).toBeInTheDocument();
    expect(screen.getByTestId("heading").textContent).toContain("Line 1");
    expect(screen.getByTestId("heading").textContent).toContain("Line 2");
    expect(screen.getByTestId("heading").textContent).toContain("Line 3");
  });

  it("should handle multiline description", () => {
    const multilineDescription = "Line 1\nLine 2\nLine 3";
    render(<Card title="Test Title" description={multilineDescription} />);

    // Check that content is rendered (newlines may be normalized)
    expect(screen.getByTestId("text")).toBeInTheDocument();
    expect(screen.getByTestId("text").textContent).toContain("Line 1");
    expect(screen.getByTestId("text").textContent).toContain("Line 2");
    expect(screen.getByTestId("text").textContent).toContain("Line 3");
  });

  it("should handle complex icon component", () => {
    const ComplexIcon = () => (
      <div data-testid="complex-icon">
        <span>🎯</span>
        <span>Complex</span>
      </div>
    );

    render(<Card title="Test Title" icon={<ComplexIcon />} />);

    expect(screen.getByTestId("complex-icon")).toBeInTheDocument();
    expect(screen.getByText("🎯")).toBeInTheDocument();
    expect(screen.getByText("Complex")).toBeInTheDocument();
  });

  it("should handle complex children", () => {
    render(
      <Card title="Test Title">
        <div data-testid="complex-child">
          <button>Click me</button>
          <input placeholder="Enter text" />
          <ul>
            <li>Item 1</li>
            <li>Item 2</li>
          </ul>
        </div>
      </Card>,
    );

    expect(screen.getByTestId("complex-child")).toBeInTheDocument();
    expect(screen.getByText("Click me")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Enter text")).toBeInTheDocument();
    expect(screen.getByText("Item 1")).toBeInTheDocument();
    expect(screen.getByText("Item 2")).toBeInTheDocument();
  });

  it("should handle null icon", () => {
    render(<Card title="Test Title" icon={null} />);

    expect(screen.getByText("Test Title")).toBeInTheDocument();
    expect(screen.queryByTestId("test-icon")).not.toBeInTheDocument();
  });

  it("should handle undefined icon", () => {
    render(<Card title="Test Title" icon={undefined} />);

    expect(screen.getByText("Test Title")).toBeInTheDocument();
    expect(screen.queryByTestId("test-icon")).not.toBeInTheDocument();
  });
});
