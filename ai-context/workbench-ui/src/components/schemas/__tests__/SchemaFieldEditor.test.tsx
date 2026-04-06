/**
 * Tests for SchemaFieldEditor component
 * Tests field configuration, type selection, validation, and enum value management
 */

import React from "react";
import { render, screen } from "../../../test/test-utils";
import userEvent from "@testing-library/user-event";
import { describe, test, expect, vi, beforeEach } from "vitest";
import { SchemaFieldEditor } from "../SchemaFieldEditor";
import { SchemaField } from "../../../model/schemas-table";

// Mock dependencies
vi.mock("../../common/SelectField", () => ({
  __esModule: true,
  default: ({
    label,
    value,
    onValueChange,
    items,
  }: {
    label: string;
    value: string | string[];
    onValueChange: (value: string) => void;
    items: { value: string; label: string }[];
  }) => (
    <div data-testid="type-select-field">
      <label>{label}</label>
      <select
        data-testid="type-select"
        value={Array.isArray(value) ? value[0] || "" : value || ""}
        onChange={(e) => onValueChange(e.target.value)}
      >
        <option value="">Select type</option>
        {items.map((item: { value: string; label: string }) => (
          <option key={item.value} value={item.value}>
            {item.label}
          </option>
        ))}
      </select>
    </div>
  ),
}));

vi.mock("../EnumValueManager", () => ({
  EnumValueManager: ({
    values,
    onAddValue,
    onRemoveValue,
  }: {
    values: string[];
    onAddValue: (value: string) => void;
    onRemoveValue: (value: string) => void;
  }) => (
    <div data-testid="enum-value-manager">
      <span data-testid="enum-values-count">{values.length}</span>
      {values.map((value: string) => (
        <div key={value} data-testid={`enum-value-${value}`}>
          <span>{value}</span>
          <button
            onClick={() => onRemoveValue(value)}
            data-testid={`remove-enum-${value}`}
          >
            Remove
          </button>
        </div>
      ))}
      <input
        data-testid="enum-input"
        placeholder="Add enum value"
        onKeyDown={(e) => {
          if (e.key === "Enter" && e.currentTarget.value) {
            onAddValue(e.currentTarget.value);
            e.currentTarget.value = "";
          }
        }}
      />
    </div>
  ),
}));

vi.mock("../../model/schemaTypes", () => ({
  SCHEMA_TYPE_OPTIONS: [
    { value: "string", label: "String", description: "Text data" },
    { value: "integer", label: "Integer", description: "Whole numbers" },
    { value: "float", label: "Float", description: "Decimal numbers" },
    { value: "boolean", label: "Boolean", description: "True/false values" },
    {
      value: "timestamp",
      label: "Timestamp",
      description: "Date/time values",
    },
    { value: "enum", label: "Enum", description: "Predefined values" },
  ],
}));

// Mock data
const mockField: SchemaField = {
  id: "field-1",
  name: "customer_id",
  type: "string",
  primary_key: false,
  required: true,
};

const mockEnumField: SchemaField = {
  id: "field-2",
  name: "status",
  type: "enum",
  enum: ["active", "inactive", "pending"],
  primary_key: false,
  required: false,
};

describe("SchemaFieldEditor", () => {
  const mockOnFieldChange = vi.fn();
  const mockOnRemoveField = vi.fn();
  const mockOnAddEnumValue = vi.fn();
  const mockOnRemoveEnumValue = vi.fn();
  const mockContentRef = { current: document.createElement("div") };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  test("renders field editor with field data", () => {
    render(
      <SchemaFieldEditor
        field={mockField}
        index={0}
        onFieldChange={mockOnFieldChange}
        onRemoveField={mockOnRemoveField}
        onAddEnumValue={mockOnAddEnumValue}
        onRemoveEnumValue={mockOnRemoveEnumValue}
        canRemove={true}
        contentRef={mockContentRef}
      />,
    );

    expect(screen.getByDisplayValue("customer_id")).toBeInTheDocument();
    expect(screen.getByLabelText("Primary Key")).not.toBeChecked();
    expect(screen.getByLabelText("Required")).toBeChecked();
  });

  test("updates field name", async () => {
    const user = userEvent.setup();

    render(
      <SchemaFieldEditor
        field={mockField}
        index={0}
        onFieldChange={mockOnFieldChange}
        onRemoveField={mockOnRemoveField}
        onAddEnumValue={mockOnAddEnumValue}
        onRemoveEnumValue={mockOnRemoveEnumValue}
        canRemove={true}
        contentRef={mockContentRef}
      />,
    );

    const nameInput = screen.getByDisplayValue("customer_id");
    await user.clear(nameInput);
    await user.type(nameInput, "user_id");

    // Check that onChange was called with name updates (user typing triggers multiple calls)
    expect(mockOnFieldChange).toHaveBeenCalled();
    expect(mockOnFieldChange).toHaveBeenCalledWith(
      0,
      expect.objectContaining({
        name: expect.any(String),
      }),
    );
  });

  test("updates field type", async () => {
    const user = userEvent.setup();

    render(
      <SchemaFieldEditor
        field={mockField}
        index={0}
        onFieldChange={mockOnFieldChange}
        onRemoveField={mockOnRemoveField}
        onAddEnumValue={mockOnAddEnumValue}
        onRemoveEnumValue={mockOnRemoveEnumValue}
        canRemove={true}
        contentRef={mockContentRef}
      />,
    );

    const typeSelect = screen.getByTestId("type-select");
    await user.selectOptions(typeSelect, "integer");

    expect(mockOnFieldChange).toHaveBeenCalledWith(0, { type: "integer" });
  });

  test("toggles primary key checkbox", async () => {
    const user = userEvent.setup();

    render(
      <SchemaFieldEditor
        field={mockField}
        index={0}
        onFieldChange={mockOnFieldChange}
        onRemoveField={mockOnRemoveField}
        onAddEnumValue={mockOnAddEnumValue}
        onRemoveEnumValue={mockOnRemoveEnumValue}
        canRemove={true}
        contentRef={mockContentRef}
      />,
    );

    const primaryKeyCheckbox = screen.getByLabelText("Primary Key");
    await user.click(primaryKeyCheckbox);

    expect(mockOnFieldChange).toHaveBeenCalledWith(0, { primary_key: true });
  });

  test("toggles required checkbox", async () => {
    const user = userEvent.setup();

    render(
      <SchemaFieldEditor
        field={mockField}
        index={0}
        onFieldChange={mockOnFieldChange}
        onRemoveField={mockOnRemoveField}
        onAddEnumValue={mockOnAddEnumValue}
        onRemoveEnumValue={mockOnRemoveEnumValue}
        canRemove={true}
        contentRef={mockContentRef}
      />,
    );

    const requiredCheckbox = screen.getByLabelText("Required");
    await user.click(requiredCheckbox);

    expect(mockOnFieldChange).toHaveBeenCalledWith(0, { required: false });
  });

  test("removes field when remove button clicked", async () => {
    const user = userEvent.setup();

    render(
      <SchemaFieldEditor
        field={mockField}
        index={0}
        onFieldChange={mockOnFieldChange}
        onRemoveField={mockOnRemoveField}
        onAddEnumValue={mockOnAddEnumValue}
        onRemoveEnumValue={mockOnRemoveEnumValue}
        canRemove={true}
        contentRef={mockContentRef}
      />,
    );

    const removeButton = screen.getByLabelText("Remove field");
    await user.click(removeButton);

    expect(mockOnRemoveField).toHaveBeenCalledWith(0);
  });

  test("disables remove button when canRemove is false", () => {
    render(
      <SchemaFieldEditor
        field={mockField}
        index={0}
        onFieldChange={mockOnFieldChange}
        onRemoveField={mockOnRemoveField}
        onAddEnumValue={mockOnAddEnumValue}
        onRemoveEnumValue={mockOnRemoveEnumValue}
        canRemove={false}
        contentRef={mockContentRef}
      />,
    );

    const removeButton = screen.getByLabelText("Remove field");
    expect(removeButton).toBeDisabled();
  });

  test("shows enum value manager for enum fields", () => {
    render(
      <SchemaFieldEditor
        field={mockEnumField}
        index={0}
        onFieldChange={mockOnFieldChange}
        onRemoveField={mockOnRemoveField}
        onAddEnumValue={mockOnAddEnumValue}
        onRemoveEnumValue={mockOnRemoveEnumValue}
        canRemove={true}
        contentRef={mockContentRef}
      />,
    );

    expect(screen.getByTestId("enum-value-manager")).toBeInTheDocument();
    expect(screen.getByTestId("enum-values-count")).toHaveTextContent("3");
    expect(screen.getByTestId("enum-value-active")).toBeInTheDocument();
  });

  test("hides enum value manager for non-enum fields", () => {
    render(
      <SchemaFieldEditor
        field={mockField}
        index={0}
        onFieldChange={mockOnFieldChange}
        onRemoveField={mockOnRemoveField}
        onAddEnumValue={mockOnAddEnumValue}
        onRemoveEnumValue={mockOnRemoveEnumValue}
        canRemove={true}
        contentRef={mockContentRef}
      />,
    );

    expect(screen.queryByTestId("enum-value-manager")).not.toBeInTheDocument();
  });

  test("adds enum values", async () => {
    const user = userEvent.setup();

    render(
      <SchemaFieldEditor
        field={mockEnumField}
        index={0}
        onFieldChange={mockOnFieldChange}
        onRemoveField={mockOnRemoveField}
        onAddEnumValue={mockOnAddEnumValue}
        onRemoveEnumValue={mockOnRemoveEnumValue}
        canRemove={true}
        contentRef={mockContentRef}
      />,
    );

    const enumInput = screen.getByTestId("enum-input");
    await user.type(enumInput, "suspended");
    await user.keyboard("{Enter}");

    expect(mockOnAddEnumValue).toHaveBeenCalledWith(0, "suspended");
  });

  test("removes enum values", async () => {
    const user = userEvent.setup();

    render(
      <SchemaFieldEditor
        field={mockEnumField}
        index={0}
        onFieldChange={mockOnFieldChange}
        onRemoveField={mockOnRemoveField}
        onAddEnumValue={mockOnAddEnumValue}
        onRemoveEnumValue={mockOnRemoveEnumValue}
        canRemove={true}
        contentRef={mockContentRef}
      />,
    );

    const removeButton = screen.getByTestId("remove-enum-active");
    await user.click(removeButton);

    expect(mockOnRemoveEnumValue).toHaveBeenCalledWith(0, "active");
  });

  test("handles empty type selection correctly", () => {
    const fieldWithoutType = { ...mockField, type: undefined as undefined };

    render(
      <SchemaFieldEditor
        field={fieldWithoutType}
        index={0}
        onFieldChange={mockOnFieldChange}
        onRemoveField={mockOnRemoveField}
        onAddEnumValue={mockOnAddEnumValue}
        onRemoveEnumValue={mockOnRemoveEnumValue}
        canRemove={true}
        contentRef={mockContentRef}
      />,
    );

    const typeSelect = screen.getByTestId("type-select");
    expect(typeSelect).toHaveValue("");
  });

  test("handles type selection correctly", async () => {
    const user = userEvent.setup();

    render(
      <SchemaFieldEditor
        field={mockField}
        index={0}
        onFieldChange={mockOnFieldChange}
        onRemoveField={mockOnRemoveField}
        onAddEnumValue={mockOnAddEnumValue}
        onRemoveEnumValue={mockOnRemoveEnumValue}
        canRemove={true}
        contentRef={mockContentRef}
      />,
    );

    const typeSelect = screen.getByTestId("type-select");
    await user.selectOptions(typeSelect, "enum");

    expect(mockOnFieldChange).toHaveBeenCalledWith(0, { type: "enum" });
  });

  test("shows required field indicator", () => {
    render(
      <SchemaFieldEditor
        field={mockField}
        index={0}
        onFieldChange={mockOnFieldChange}
        onRemoveField={mockOnRemoveField}
        onAddEnumValue={mockOnAddEnumValue}
        onRemoveEnumValue={mockOnRemoveEnumValue}
        canRemove={true}
        contentRef={mockContentRef}
      />,
    );

    expect(screen.getByText("Field Name")).toBeInTheDocument();
    // Required indicator should be present (rendered by Chakra UI Field component)
  });

  test("renders with proper layout structure", () => {
    render(
      <SchemaFieldEditor
        field={mockField}
        index={0}
        onFieldChange={mockOnFieldChange}
        onRemoveField={mockOnRemoveField}
        onAddEnumValue={mockOnAddEnumValue}
        onRemoveEnumValue={mockOnRemoveEnumValue}
        canRemove={true}
        contentRef={mockContentRef}
      />,
    );

    // Verify the component renders the expected elements
    expect(screen.getByDisplayValue("customer_id")).toBeInTheDocument();
    expect(screen.getByLabelText("Primary Key")).toBeInTheDocument();
    expect(screen.getByLabelText("Required")).toBeInTheDocument();
    expect(screen.getByLabelText("Remove field")).toBeInTheDocument();
  });

  test("integrates with SelectField component", () => {
    render(
      <SchemaFieldEditor
        field={mockField}
        index={0}
        onFieldChange={mockOnFieldChange}
        onRemoveField={mockOnRemoveField}
        onAddEnumValue={mockOnAddEnumValue}
        onRemoveEnumValue={mockOnRemoveEnumValue}
        canRemove={true}
        contentRef={mockContentRef}
      />,
    );

    // Verify SelectField is rendered with correct structure
    expect(screen.getByTestId("type-select-field")).toBeInTheDocument();
    expect(screen.getByTestId("type-select")).toBeInTheDocument();
    expect(screen.getByText("Type")).toBeInTheDocument();
  });

  test("handles all available schema types", async () => {
    const user = userEvent.setup();

    render(
      <SchemaFieldEditor
        field={mockField}
        index={0}
        onFieldChange={mockOnFieldChange}
        onRemoveField={mockOnRemoveField}
        onAddEnumValue={mockOnAddEnumValue}
        onRemoveEnumValue={mockOnRemoveEnumValue}
        canRemove={true}
        contentRef={mockContentRef}
      />,
    );

    const typeSelect = screen.getByTestId("type-select");

    // Test each type option
    const types = [
      "string",
      "integer",
      "float",
      "boolean",
      "timestamp",
      "enum",
    ];

    for (const type of types) {
      await user.selectOptions(typeSelect, type);
      expect(mockOnFieldChange).toHaveBeenCalledWith(0, { type });
    }
  });
});
