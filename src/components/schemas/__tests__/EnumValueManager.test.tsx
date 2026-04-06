/**
 * Tests for EnumValueManager component
 * Tests enum value addition, removal, validation, and user interactions
 */

import React from "react";
import { render, screen, fireEvent } from "../../../test/test-utils";
import userEvent from "@testing-library/user-event";
import { describe, test, expect, vi, beforeEach } from "vitest";
import { EnumValueManager } from "../EnumValueManager";

describe("EnumValueManager", () => {
  const mockOnAddValue = vi.fn();
  const mockOnRemoveValue = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  test("renders with no values", () => {
    render(
      <EnumValueManager
        values={[]}
        onAddValue={mockOnAddValue}
        onRemoveValue={mockOnRemoveValue}
      />,
    );

    expect(screen.getByText("Enum Values")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Add enum value")).toBeInTheDocument();
    expect(screen.getByText("No values added yet")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add" })).toBeDisabled();
  });

  test("renders existing values", () => {
    const values = ["active", "inactive", "pending"];

    render(
      <EnumValueManager
        values={values}
        onAddValue={mockOnAddValue}
        onRemoveValue={mockOnRemoveValue}
      />,
    );

    expect(screen.getByText("active")).toBeInTheDocument();
    expect(screen.getByText("inactive")).toBeInTheDocument();
    expect(screen.getByText("pending")).toBeInTheDocument();
    expect(screen.queryByText("No values added yet")).not.toBeInTheDocument();
  });

  test("adds new value using button", async () => {
    const user = userEvent.setup();

    render(
      <EnumValueManager
        values={[]}
        onAddValue={mockOnAddValue}
        onRemoveValue={mockOnRemoveValue}
      />,
    );

    const input = screen.getByPlaceholderText("Add enum value");
    const addButton = screen.getByRole("button", { name: "Add" });

    await user.type(input, "new_value");
    await user.click(addButton);

    expect(mockOnAddValue).toHaveBeenCalledWith("new_value");
  });

  test("adds new value using Enter key", async () => {
    const user = userEvent.setup();

    render(
      <EnumValueManager
        values={[]}
        onAddValue={mockOnAddValue}
        onRemoveValue={mockOnRemoveValue}
      />,
    );

    const input = screen.getByPlaceholderText("Add enum value");
    await user.type(input, "new_value");
    await user.keyboard("{Enter}");

    expect(mockOnAddValue).toHaveBeenCalledWith("new_value");
  });

  test("clears input after adding value", async () => {
    const user = userEvent.setup();

    render(
      <EnumValueManager
        values={[]}
        onAddValue={mockOnAddValue}
        onRemoveValue={mockOnRemoveValue}
      />,
    );

    const input = screen.getByPlaceholderText("Add enum value");
    await user.type(input, "new_value");
    await user.keyboard("{Enter}");

    expect(input).toHaveValue("");
  });

  test("focuses input after adding value", async () => {
    const user = userEvent.setup();

    render(
      <EnumValueManager
        values={[]}
        onAddValue={mockOnAddValue}
        onRemoveValue={mockOnRemoveValue}
      />,
    );

    const input = screen.getByPlaceholderText("Add enum value");
    await user.type(input, "new_value");
    await user.keyboard("{Enter}");

    expect(input).toHaveFocus();
  });

  test("trims whitespace from input value", async () => {
    const user = userEvent.setup();

    render(
      <EnumValueManager
        values={[]}
        onAddValue={mockOnAddValue}
        onRemoveValue={mockOnRemoveValue}
      />,
    );

    const input = screen.getByPlaceholderText("Add enum value");
    await user.type(input, "  new_value  ");
    await user.keyboard("{Enter}");

    expect(mockOnAddValue).toHaveBeenCalledWith("new_value");
  });

  test("disables add button for empty input", () => {
    render(
      <EnumValueManager
        values={[]}
        onAddValue={mockOnAddValue}
        onRemoveValue={mockOnRemoveValue}
      />,
    );

    const addButton = screen.getByRole("button", { name: "Add" });
    expect(addButton).toBeDisabled();
  });

  test("disables add button for whitespace-only input", async () => {
    const user = userEvent.setup();

    render(
      <EnumValueManager
        values={[]}
        onAddValue={mockOnAddValue}
        onRemoveValue={mockOnRemoveValue}
      />,
    );

    const input = screen.getByPlaceholderText("Add enum value");
    const addButton = screen.getByRole("button", { name: "Add" });

    await user.type(input, "   ");
    expect(addButton).toBeDisabled();
  });

  test("prevents adding duplicate values", async () => {
    const user = userEvent.setup();
    const values = ["active", "inactive"];

    render(
      <EnumValueManager
        values={values}
        onAddValue={mockOnAddValue}
        onRemoveValue={mockOnRemoveValue}
      />,
    );

    const input = screen.getByPlaceholderText("Add enum value");
    const addButton = screen.getByRole("button", { name: "Add" });

    await user.type(input, "active");
    expect(addButton).toBeDisabled();
  });

  test("prevents adding duplicate values with different case/whitespace", async () => {
    const user = userEvent.setup();
    const values = ["active"];

    render(
      <EnumValueManager
        values={values}
        onAddValue={mockOnAddValue}
        onRemoveValue={mockOnRemoveValue}
      />,
    );

    const input = screen.getByPlaceholderText("Add enum value");
    const addButton = screen.getByRole("button", { name: "Add" });

    // Test with different whitespace (should be trimmed to "active")
    await user.type(input, "  active  ");
    expect(addButton).toBeDisabled();
  });

  test("enables add button for unique values", async () => {
    const user = userEvent.setup();
    const values = ["active", "inactive"];

    render(
      <EnumValueManager
        values={values}
        onAddValue={mockOnAddValue}
        onRemoveValue={mockOnRemoveValue}
      />,
    );

    const input = screen.getByPlaceholderText("Add enum value");
    const addButton = screen.getByRole("button", { name: "Add" });

    await user.type(input, "pending");
    expect(addButton).not.toBeDisabled();
  });

  test("removes value when close button clicked", async () => {
    const user = userEvent.setup();
    const values = ["active", "inactive", "pending"];

    render(
      <EnumValueManager
        values={values}
        onAddValue={mockOnAddValue}
        onRemoveValue={mockOnRemoveValue}
      />,
    );

    const removeButton = screen.getByLabelText("Remove active");
    await user.click(removeButton);

    expect(mockOnRemoveValue).toHaveBeenCalledWith("active");
  });

  test("displays all value badges correctly", () => {
    const values = ["active", "inactive", "pending", "suspended"];

    render(
      <EnumValueManager
        values={values}
        onAddValue={mockOnAddValue}
        onRemoveValue={mockOnRemoveValue}
      />,
    );

    values.forEach((value) => {
      expect(screen.getByText(value)).toBeInTheDocument();
      expect(screen.getByLabelText(`Remove ${value}`)).toBeInTheDocument();
    });
  });

  test("handles Enter key only on keyPress event", async () => {
    const user = userEvent.setup();

    render(
      <EnumValueManager
        values={[]}
        onAddValue={mockOnAddValue}
        onRemoveValue={mockOnRemoveValue}
      />,
    );

    const input = screen.getByPlaceholderText("Add enum value");
    await user.type(input, "test_value");

    // Simulate other keys that should not trigger add
    fireEvent.keyPress(input, { key: "Tab" });
    fireEvent.keyPress(input, { key: "Escape" });
    fireEvent.keyPress(input, { key: "ArrowDown" });

    expect(mockOnAddValue).not.toHaveBeenCalled();

    // Now test Enter key - should trigger the add function
    await user.keyboard("{Enter}");
    expect(mockOnAddValue).toHaveBeenCalledWith("test_value");
  });

  test("handles keyPress events correctly", async () => {
    const user = userEvent.setup();

    render(
      <EnumValueManager
        values={[]}
        onAddValue={mockOnAddValue}
        onRemoveValue={mockOnRemoveValue}
      />,
    );

    const input = screen.getByPlaceholderText("Add enum value");
    await user.type(input, "test_value");

    // Test that Enter key triggers add functionality
    await user.keyboard("{Enter}");

    expect(mockOnAddValue).toHaveBeenCalledWith("test_value");
    expect(input).toHaveValue(""); // Should be cleared after adding
  });

  test("handles empty values array gracefully", () => {
    render(
      <EnumValueManager
        values={[]}
        onAddValue={mockOnAddValue}
        onRemoveValue={mockOnRemoveValue}
      />,
    );

    expect(screen.getByText("No values added yet")).toBeInTheDocument();
  });

  test("handles undefined values prop", () => {
    render(
      <EnumValueManager
        values={undefined as undefined}
        onAddValue={mockOnAddValue}
        onRemoveValue={mockOnRemoveValue}
      />,
    );

    // Should default to empty array and show empty state
    expect(screen.getByText("No values added yet")).toBeInTheDocument();
  });

  test("maintains input value state correctly", async () => {
    const user = userEvent.setup();

    render(
      <EnumValueManager
        values={[]}
        onAddValue={mockOnAddValue}
        onRemoveValue={mockOnRemoveValue}
      />,
    );

    const input = screen.getByPlaceholderText("Add enum value");

    // Type some text
    await user.type(input, "partial");
    expect(input).toHaveValue("partial");

    // Clear and type new text
    await user.clear(input);
    await user.type(input, "complete");
    expect(input).toHaveValue("complete");
  });

  test("renders badges with correct styling props", () => {
    const values = ["test_value"];

    render(
      <EnumValueManager
        values={values}
        onAddValue={mockOnAddValue}
        onRemoveValue={mockOnRemoveValue}
      />,
    );

    const badge = screen.getByText("test_value").closest(".chakra-badge");
    expect(badge).toHaveClass("chakra-badge");
  });

  test("input ref functionality works", async () => {
    const user = userEvent.setup();

    render(
      <EnumValueManager
        values={[]}
        onAddValue={mockOnAddValue}
        onRemoveValue={mockOnRemoveValue}
      />,
    );

    const input = screen.getByPlaceholderText("Add enum value");

    // Add a value which should refocus the input
    await user.type(input, "test");
    await user.keyboard("{Enter}");

    // Input should be focused after adding
    expect(input).toHaveFocus();
  });

  test("updates input value state on change", async () => {
    const user = userEvent.setup();

    render(
      <EnumValueManager
        values={[]}
        onAddValue={mockOnAddValue}
        onRemoveValue={mockOnRemoveValue}
      />,
    );

    const input = screen.getByPlaceholderText("Add enum value");
    const addButton = screen.getByRole("button", { name: "Add" });

    // Initially disabled
    expect(addButton).toBeDisabled();

    // Type to enable
    await user.type(input, "test");
    expect(addButton).not.toBeDisabled();

    // Clear to disable again
    await user.clear(input);
    expect(addButton).toBeDisabled();
  });
});
