import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import TextField from "../TextField";

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
    "required",
  ];
  const filtered = { ...props };
  chakraProps.forEach((prop) => delete filtered[prop]);
  return filtered;
};

// Mock Chakra UI components
vi.mock("@chakra-ui/react", () => ({
  Field: {
    Root: ({
      children,
      ...props
    }: React.PropsWithChildren<Record<string, unknown>>) => (
      <div data-testid="field-root" {...filterChakraProps(props)}>
        {children}
      </div>
    ),
    Label: ({
      children,
      ...props
    }: React.PropsWithChildren<Record<string, unknown>>) => (
      <label data-testid="field-label" {...filterChakraProps(props)}>
        {children}
      </label>
    ),
    RequiredIndicator: ({ ...props }: Record<string, unknown>) => (
      <span data-testid="required-indicator" {...filterChakraProps(props)}>
        *
      </span>
    ),
    HelperText: ({
      children,
      ...props
    }: React.PropsWithChildren<Record<string, unknown>>) => (
      <div data-testid="helper-text" {...filterChakraProps(props)}>
        {children}
      </div>
    ),
  },
  Input: ({
    value,
    onChange,
    placeholder,
    ...props
  }: {
    value?: string;
    onChange?: React.ChangeEventHandler<HTMLInputElement>;
    placeholder?: string;
  } & Record<string, unknown>) => (
    <input
      data-testid="text-input"
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      {...filterChakraProps(props)}
    />
  ),
}));

describe("TextField", () => {
  const defaultProps = {
    label: "Test Label",
    value: "",
    onValueChange: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should render with label and input", () => {
    render(<TextField {...defaultProps} />);

    expect(screen.getByTestId("field-label")).toBeInTheDocument();
    expect(screen.getByText("Test Label")).toBeInTheDocument();
    expect(screen.getByTestId("text-input")).toBeInTheDocument();
  });

  it("should display the current value", () => {
    render(<TextField {...defaultProps} value="test value" />);

    const input = screen.getByTestId("text-input");
    expect(input).toHaveValue("test value");
  });

  it("should call onValueChange when input value changes", async () => {
    const user = userEvent.setup();
    const mockOnValueChange = vi.fn();

    render(<TextField {...defaultProps} onValueChange={mockOnValueChange} />);

    const input = screen.getByTestId("text-input");
    await user.type(input, "new value");

    expect(mockOnValueChange).toHaveBeenCalledWith("n");
    expect(mockOnValueChange).toHaveBeenCalledWith("e");
    expect(mockOnValueChange).toHaveBeenCalledWith("w");
    expect(mockOnValueChange).toHaveBeenCalledWith(" ");
    expect(mockOnValueChange).toHaveBeenCalledWith("v");
    expect(mockOnValueChange).toHaveBeenCalledWith("a");
    expect(mockOnValueChange).toHaveBeenCalledWith("l");
    expect(mockOnValueChange).toHaveBeenCalledWith("u");
    expect(mockOnValueChange).toHaveBeenCalledWith("e");
  });

  it("should handle onChange event correctly", () => {
    const mockOnValueChange = vi.fn();

    render(<TextField {...defaultProps} onValueChange={mockOnValueChange} />);

    const input = screen.getByTestId("text-input");
    fireEvent.change(input, { target: { value: "test input" } });

    expect(mockOnValueChange).toHaveBeenCalledWith("test input");
  });

  it("should display placeholder when provided", () => {
    render(<TextField {...defaultProps} placeholder="Enter text here" />);

    const input = screen.getByTestId("text-input");
    expect(input).toHaveAttribute("placeholder", "Enter text here");
  });

  it("should show required indicator when required is true", () => {
    render(<TextField {...defaultProps} required />);

    expect(screen.getByTestId("required-indicator")).toBeInTheDocument();
    expect(screen.getByText("*")).toBeInTheDocument();
  });

  it("should not show required indicator when required is false", () => {
    render(<TextField {...defaultProps} required={false} />);

    expect(screen.queryByTestId("required-indicator")).not.toBeInTheDocument();
  });

  it("should not show required indicator when required is undefined", () => {
    render(<TextField {...defaultProps} />);

    expect(screen.queryByTestId("required-indicator")).not.toBeInTheDocument();
  });

  it("should display helper text when provided", () => {
    render(<TextField {...defaultProps} helperText="This is helper text" />);

    expect(screen.getByTestId("helper-text")).toBeInTheDocument();
    expect(screen.getByText("This is helper text")).toBeInTheDocument();
  });

  it("should not display helper text when not provided", () => {
    render(<TextField {...defaultProps} />);

    expect(screen.queryByTestId("helper-text")).not.toBeInTheDocument();
  });

  it("should handle empty string value", () => {
    render(<TextField {...defaultProps} value="" />);

    const input = screen.getByTestId("text-input");
    expect(input).toHaveValue("");
  });

  it("should handle special characters in value", () => {
    const specialValue = "!@#$%^&*()_+{}[]|\\:;\"'<>,.?/~`";
    render(<TextField {...defaultProps} value={specialValue} />);

    const input = screen.getByTestId("text-input");
    expect(input).toHaveValue(specialValue);
  });

  it("should handle multiline text in value", () => {
    const multilineValue = "Line 1\nLine 2\nLine 3";
    render(<TextField {...defaultProps} value={multilineValue} />);

    const input = screen.getByTestId("text-input");
    // Check that the value contains the expected content
    expect(input).toBeInTheDocument();
    expect(input.getAttribute("value")).toContain("Line 1");
    expect(input.getAttribute("value")).toContain("Line 2");
    expect(input.getAttribute("value")).toContain("Line 3");
  });

  it("should render field root structure", () => {
    render(<TextField {...defaultProps} required />);

    const fieldRoot = screen.getByTestId("field-root");
    expect(fieldRoot).toBeInTheDocument();
    expect(fieldRoot).toContainElement(screen.getByTestId("field-label"));
    expect(fieldRoot).toContainElement(screen.getByTestId("text-input"));
  });

  it("should handle long text values", () => {
    const longValue = "a".repeat(1000);
    render(<TextField {...defaultProps} value={longValue} />);

    const input = screen.getByTestId("text-input");
    expect(input).toHaveValue(longValue);
  });

  it("should handle rapid input changes", async () => {
    const user = userEvent.setup();
    const mockOnValueChange = vi.fn();

    render(<TextField {...defaultProps} onValueChange={mockOnValueChange} />);

    const input = screen.getByTestId("text-input");
    await user.type(input, "abc", { delay: 1 });

    expect(mockOnValueChange).toHaveBeenCalledTimes(3);
    expect(mockOnValueChange).toHaveBeenNthCalledWith(1, "a");
    expect(mockOnValueChange).toHaveBeenNthCalledWith(2, "b");
    expect(mockOnValueChange).toHaveBeenNthCalledWith(3, "c");
  });

  it("should clear input when value changes to empty string", () => {
    const { rerender } = render(
      <TextField {...defaultProps} value="initial value" />,
    );

    let input = screen.getByTestId("text-input");
    expect(input).toHaveValue("initial value");

    rerender(<TextField {...defaultProps} value="" />);

    input = screen.getByTestId("text-input");
    expect(input).toHaveValue("");
  });
});
