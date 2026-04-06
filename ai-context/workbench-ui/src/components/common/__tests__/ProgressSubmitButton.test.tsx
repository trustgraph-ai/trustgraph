import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ProgressSubmitButton from "../ProgressSubmitButton";

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
  Button: ({
    children,
    onClick,
    disabled,
    loading,
    ...props
  }: React.PropsWithChildren<
    {
      onClick?: React.MouseEventHandler<HTMLButtonElement>;
      disabled?: boolean;
      loading?: boolean;
    } & Record<string, unknown>
  >) => (
    <button
      data-testid="progress-button"
      onClick={onClick}
      disabled={disabled}
      data-loading={loading}
      {...filterChakraProps(props)}
    >
      {children}
    </button>
  ),
}));

// Mock lucide-react icon
vi.mock("lucide-react", () => ({
  SendHorizontal: () => <div data-testid="send-icon">Send</div>,
}));

describe("ProgressSubmitButton", () => {
  const mockOnClick = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should render button with correct content", () => {
    render(
      <ProgressSubmitButton
        disabled={false}
        working={false}
        onClick={mockOnClick}
      />,
    );

    expect(screen.getByTestId("progress-button")).toBeInTheDocument();
    expect(screen.getByTestId("progress-button")).toHaveTextContent("Send");
    expect(screen.getByTestId("send-icon")).toBeInTheDocument();
  });

  it("should render within Box wrapper", () => {
    render(
      <ProgressSubmitButton
        disabled={false}
        working={false}
        onClick={mockOnClick}
      />,
    );

    expect(screen.getByTestId("box")).toBeInTheDocument();
    expect(screen.getByTestId("box")).toContainElement(
      screen.getByTestId("progress-button"),
    );
  });

  it("should call onClick when button is clicked", () => {
    render(
      <ProgressSubmitButton
        disabled={false}
        working={false}
        onClick={mockOnClick}
      />,
    );

    fireEvent.click(screen.getByTestId("progress-button"));
    expect(mockOnClick).toHaveBeenCalledTimes(1);
  });

  it("should be disabled when disabled prop is true", () => {
    render(
      <ProgressSubmitButton
        disabled={true}
        working={false}
        onClick={mockOnClick}
      />,
    );

    expect(screen.getByTestId("progress-button")).toBeDisabled();
  });

  it("should not be disabled when disabled prop is false", () => {
    render(
      <ProgressSubmitButton
        disabled={false}
        working={false}
        onClick={mockOnClick}
      />,
    );

    expect(screen.getByTestId("progress-button")).not.toBeDisabled();
  });

  it("should have loading state when working prop is true", () => {
    render(
      <ProgressSubmitButton
        disabled={false}
        working={true}
        onClick={mockOnClick}
      />,
    );

    expect(screen.getByTestId("progress-button")).toHaveAttribute(
      "data-loading",
      "true",
    );
  });

  it("should not have loading state when working prop is false", () => {
    render(
      <ProgressSubmitButton
        disabled={false}
        working={false}
        onClick={mockOnClick}
      />,
    );

    expect(screen.getByTestId("progress-button")).toHaveAttribute(
      "data-loading",
      "false",
    );
  });

  it("should render button with correct structure", () => {
    render(
      <ProgressSubmitButton
        disabled={false}
        working={false}
        onClick={mockOnClick}
      />,
    );

    const button = screen.getByTestId("progress-button");
    expect(button).toBeInTheDocument();
    expect(button.tagName).toBe("BUTTON");
  });

  it("should handle both disabled and working states", () => {
    render(
      <ProgressSubmitButton
        disabled={true}
        working={true}
        onClick={mockOnClick}
      />,
    );

    const button = screen.getByTestId("progress-button");
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("data-loading", "true");
  });

  it("should not call onClick when disabled", () => {
    render(
      <ProgressSubmitButton
        disabled={true}
        working={false}
        onClick={mockOnClick}
      />,
    );

    fireEvent.click(screen.getByTestId("progress-button"));
    expect(mockOnClick).not.toHaveBeenCalled();
  });

  it("should handle multiple clicks when enabled", () => {
    render(
      <ProgressSubmitButton
        disabled={false}
        working={false}
        onClick={mockOnClick}
      />,
    );

    const button = screen.getByTestId("progress-button");
    fireEvent.click(button);
    fireEvent.click(button);
    fireEvent.click(button);

    expect(mockOnClick).toHaveBeenCalledTimes(3);
  });

  it("should maintain consistent state when props change", () => {
    const { rerender } = render(
      <ProgressSubmitButton
        disabled={false}
        working={false}
        onClick={mockOnClick}
      />,
    );

    let button = screen.getByTestId("progress-button");
    expect(button).not.toBeDisabled();
    expect(button).toHaveAttribute("data-loading", "false");

    // Change to working state
    rerender(
      <ProgressSubmitButton
        disabled={false}
        working={true}
        onClick={mockOnClick}
      />,
    );

    button = screen.getByTestId("progress-button");
    expect(button).not.toBeDisabled();
    expect(button).toHaveAttribute("data-loading", "true");

    // Change to disabled state
    rerender(
      <ProgressSubmitButton
        disabled={true}
        working={false}
        onClick={mockOnClick}
      />,
    );

    button = screen.getByTestId("progress-button");
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("data-loading", "false");
  });

  it("should handle rapid state changes", () => {
    const { rerender } = render(
      <ProgressSubmitButton
        disabled={false}
        working={false}
        onClick={mockOnClick}
      />,
    );

    // Rapidly change states
    rerender(
      <ProgressSubmitButton
        disabled={true}
        working={true}
        onClick={mockOnClick}
      />,
    );

    rerender(
      <ProgressSubmitButton
        disabled={false}
        working={false}
        onClick={mockOnClick}
      />,
    );

    const button = screen.getByTestId("progress-button");
    expect(button).not.toBeDisabled();
    expect(button).toHaveAttribute("data-loading", "false");
  });

  it("should handle onClick function changes", () => {
    const newOnClick = vi.fn();

    const { rerender } = render(
      <ProgressSubmitButton
        disabled={false}
        working={false}
        onClick={mockOnClick}
      />,
    );

    fireEvent.click(screen.getByTestId("progress-button"));
    expect(mockOnClick).toHaveBeenCalledTimes(1);

    // Change onClick function
    rerender(
      <ProgressSubmitButton
        disabled={false}
        working={false}
        onClick={newOnClick}
      />,
    );

    fireEvent.click(screen.getByTestId("progress-button"));
    expect(newOnClick).toHaveBeenCalledTimes(1);
    expect(mockOnClick).toHaveBeenCalledTimes(1); // Should not be called again
  });

  it("should render icon alongside text", () => {
    render(
      <ProgressSubmitButton
        disabled={false}
        working={false}
        onClick={mockOnClick}
      />,
    );

    const button = screen.getByTestId("progress-button");
    expect(button).toHaveTextContent("Send");
    expect(screen.getByTestId("send-icon")).toBeInTheDocument();
  });

  it("should handle edge case combinations", () => {
    // Test disabled=true, working=false
    const { rerender } = render(
      <ProgressSubmitButton
        disabled={true}
        working={false}
        onClick={mockOnClick}
      />,
    );

    let button = screen.getByTestId("progress-button");
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("data-loading", "false");

    // Test disabled=false, working=true
    rerender(
      <ProgressSubmitButton
        disabled={false}
        working={true}
        onClick={mockOnClick}
      />,
    );

    button = screen.getByTestId("progress-button");
    expect(button).not.toBeDisabled();
    expect(button).toHaveAttribute("data-loading", "true");

    // Test disabled=true, working=true
    rerender(
      <ProgressSubmitButton
        disabled={true}
        working={true}
        onClick={mockOnClick}
      />,
    );

    button = screen.getByTestId("progress-button");
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("data-loading", "true");
  });
});
