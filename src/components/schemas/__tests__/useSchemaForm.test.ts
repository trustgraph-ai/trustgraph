/**
 * Tests for useSchemaForm hook
 * Tests form state management, field operations, validation, and form utilities
 */

import { renderHook, act } from "@testing-library/react";
import { describe, test, expect, vi, beforeEach } from "vitest";
import { useSchemaForm } from "../useSchemaForm";
import { Schema, SchemaField } from "../../../model/schemas-table";

// Mock uuid
vi.mock("uuid", () => ({
  v4: vi.fn(() => "mock-uuid-123"),
}));

vi.mock("../../model/schemaTypes", () => ({
  DEFAULT_FIELD: {
    name: "",
    type: "string",
    primary_key: false,
    required: false,
  },
}));

// Mock data
const mockSchema: Schema = {
  name: "User Schema",
  description: "Schema for user data",
  fields: [
    {
      id: "field-1",
      name: "user_id",
      type: "string",
      primary_key: true,
      required: true,
    },
    {
      id: "field-2",
      name: "status",
      type: "enum",
      enum: ["active", "inactive"],
      primary_key: false,
      required: false,
    },
  ],
  indexes: ["user_id", "status"],
};

describe("useSchemaForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test("initializes with default values for create mode", () => {
    const { result } = renderHook(() =>
      useSchemaForm({
        isOpen: true,
        mode: "create",
      }),
    );

    expect(result.current.id).toBe("");
    expect(result.current.name).toBe("");
    expect(result.current.description).toBe("");
    expect(result.current.fields).toHaveLength(1);
    expect(result.current.fields[0]).toEqual(
      expect.objectContaining({
        id: "mock-uuid-123",
        name: "",
        type: "string",
        primary_key: false,
        required: false,
      }),
    );
    expect(result.current.indexes).toEqual([]);
    expect(result.current.errors).toEqual([]);
  });

  test("initializes with existing schema in edit mode", () => {
    const { result } = renderHook(() =>
      useSchemaForm({
        isOpen: true,
        mode: "edit",
        schemaId: "schema-1",
        initialSchema: mockSchema,
      }),
    );

    expect(result.current.id).toBe("schema-1");
    expect(result.current.name).toBe("User Schema");
    expect(result.current.description).toBe("Schema for user data");
    expect(result.current.fields).toHaveLength(2);
    expect(result.current.indexes).toEqual(["user_id", "status"]);
  });

  test("adds UUIDs to fields that don't have them", () => {
    const schemaWithoutIds: Schema = {
      ...mockSchema,
      fields: [
        {
          name: "test_field",
          type: "string",
          primary_key: false,
          required: false,
        } as SchemaField,
      ],
    };

    const { result } = renderHook(() =>
      useSchemaForm({
        isOpen: true,
        mode: "edit",
        initialSchema: schemaWithoutIds,
      }),
    );

    expect(result.current.fields[0].id).toBe("mock-uuid-123");
  });

  test("resets form when dialog opens", () => {
    const { result, rerender } = renderHook(
      ({ isOpen, schema }) =>
        useSchemaForm({
          isOpen,
          mode: "edit",
          initialSchema: schema,
        }),
      {
        initialProps: { isOpen: false, schema: undefined },
      },
    );

    // Initially closed
    expect(result.current.name).toBe("");

    // Open with schema
    rerender({ isOpen: true, schema: mockSchema });

    expect(result.current.name).toBe("User Schema");
  });

  test("adds new field", () => {
    const { result } = renderHook(() =>
      useSchemaForm({
        isOpen: true,
        mode: "create",
      }),
    );

    act(() => {
      result.current.handleAddField();
    });

    expect(result.current.fields).toHaveLength(2);
    expect(result.current.fields[1]).toEqual(
      expect.objectContaining({
        id: "mock-uuid-123",
        name: "",
        type: "string",
        primary_key: false,
        required: false,
      }),
    );
  });

  test("removes field", () => {
    const { result } = renderHook(() =>
      useSchemaForm({
        isOpen: true,
        mode: "edit",
        initialSchema: mockSchema,
      }),
    );

    act(() => {
      result.current.handleRemoveField(1);
    });

    expect(result.current.fields).toHaveLength(1);
    expect(result.current.fields[0].name).toBe("user_id");
  });

  test("removes field from indexes when field is removed", () => {
    const { result } = renderHook(() =>
      useSchemaForm({
        isOpen: true,
        mode: "edit",
        initialSchema: mockSchema,
      }),
    );

    expect(result.current.indexes).toContain("status");

    act(() => {
      result.current.handleRemoveField(1); // Remove status field
    });

    expect(result.current.indexes).not.toContain("status");
    expect(result.current.indexes).toContain("user_id");
  });

  test("updates field properties", () => {
    const { result } = renderHook(() =>
      useSchemaForm({
        isOpen: true,
        mode: "edit",
        initialSchema: mockSchema,
      }),
    );

    act(() => {
      result.current.handleFieldChange(0, {
        name: "updated_user_id",
        required: false,
      });
    });

    expect(result.current.fields[0]).toEqual(
      expect.objectContaining({
        name: "updated_user_id",
        type: "string",
        primary_key: true,
        required: false,
      }),
    );
  });

  test("clears enum values when type changes from enum", () => {
    const { result } = renderHook(() =>
      useSchemaForm({
        isOpen: true,
        mode: "edit",
        initialSchema: mockSchema,
      }),
    );

    // Status field is enum with values
    expect(result.current.fields[1].enum).toEqual(["active", "inactive"]);

    act(() => {
      result.current.handleFieldChange(1, {
        type: "string",
      });
    });

    expect(result.current.fields[1].enum).toBeUndefined();
    expect(result.current.fields[1].type).toBe("string");
  });

  test("preserves enum values when type remains enum", () => {
    const { result } = renderHook(() =>
      useSchemaForm({
        isOpen: true,
        mode: "edit",
        initialSchema: mockSchema,
      }),
    );

    act(() => {
      result.current.handleFieldChange(1, {
        name: "updated_status",
      });
    });

    expect(result.current.fields[1].enum).toEqual(["active", "inactive"]);
  });

  test("adds enum value", () => {
    const { result } = renderHook(() =>
      useSchemaForm({
        isOpen: true,
        mode: "edit",
        initialSchema: mockSchema,
      }),
    );

    act(() => {
      result.current.handleAddEnumValue(1, "pending");
    });

    expect(result.current.fields[1].enum).toEqual([
      "active",
      "inactive",
      "pending",
    ]);
  });

  test("prevents adding duplicate enum values", () => {
    const { result } = renderHook(() =>
      useSchemaForm({
        isOpen: true,
        mode: "edit",
        initialSchema: mockSchema,
      }),
    );

    act(() => {
      result.current.handleAddEnumValue(1, "active");
    });

    expect(result.current.fields[1].enum).toEqual(["active", "inactive"]);
  });

  test("removes enum value", () => {
    const { result } = renderHook(() =>
      useSchemaForm({
        isOpen: true,
        mode: "edit",
        initialSchema: mockSchema,
      }),
    );

    act(() => {
      result.current.handleRemoveEnumValue(1, "active");
    });

    expect(result.current.fields[1].enum).toEqual(["inactive"]);
  });

  test("handles enum operations on field without enum values", () => {
    const { result } = renderHook(() =>
      useSchemaForm({
        isOpen: true,
        mode: "create",
      }),
    );

    // Add enum value to string field (which has no enum property)
    act(() => {
      result.current.handleAddEnumValue(0, "test_value");
    });

    expect(result.current.fields[0].enum).toEqual(["test_value"]);
  });

  test("adds index", () => {
    const { result } = renderHook(() =>
      useSchemaForm({
        isOpen: true,
        mode: "create",
      }),
    );

    act(() => {
      result.current.setNewIndex("test_index");
    });

    act(() => {
      result.current.handleAddIndex();
    });

    expect(result.current.indexes).toContain("test_index");
    expect(result.current.newIndex).toBe("");
  });

  test("prevents adding duplicate indexes", () => {
    const { result } = renderHook(() =>
      useSchemaForm({
        isOpen: true,
        mode: "edit",
        initialSchema: mockSchema,
      }),
    );

    act(() => {
      result.current.setNewIndex("user_id");
    });

    act(() => {
      result.current.handleAddIndex();
    });

    expect(result.current.indexes).toEqual(["user_id", "status"]);
  });

  test("removes index", () => {
    const { result } = renderHook(() =>
      useSchemaForm({
        isOpen: true,
        mode: "edit",
        initialSchema: mockSchema,
      }),
    );

    act(() => {
      result.current.handleRemoveIndex("user_id");
    });

    expect(result.current.indexes).toEqual(["status"]);
  });

  test("resets form to default state", () => {
    const { result } = renderHook(() =>
      useSchemaForm({
        isOpen: true,
        mode: "edit",
        initialSchema: mockSchema,
      }),
    );

    act(() => {
      result.current.resetForm();
    });

    expect(result.current.id).toBe("");
    expect(result.current.name).toBe("");
    expect(result.current.description).toBe("");
    expect(result.current.fields).toHaveLength(1);
    expect(result.current.indexes).toEqual([]);
    expect(result.current.errors).toEqual([]);
  });

  test("generates schema object", () => {
    const { result } = renderHook(() =>
      useSchemaForm({
        isOpen: true,
        mode: "edit",
        initialSchema: mockSchema,
      }),
    );

    const schema = result.current.getSchema();

    expect(schema).toEqual({
      name: "User Schema",
      description: "Schema for user data",
      fields: expect.arrayContaining([
        expect.objectContaining({
          name: "user_id",
          type: "string",
        }),
      ]),
      indexes: ["user_id", "status"],
    });
  });

  test("omits indexes from schema when empty", () => {
    const { result } = renderHook(() =>
      useSchemaForm({
        isOpen: true,
        mode: "create",
      }),
    );

    const schema = result.current.getSchema();

    expect(schema.indexes).toBeUndefined();
  });

  test("updates all form fields through setters", () => {
    const { result } = renderHook(() =>
      useSchemaForm({
        isOpen: true,
        mode: "create",
      }),
    );

    act(() => {
      result.current.setId("test-id");
      result.current.setName("Test Schema");
      result.current.setDescription("Test Description");
      result.current.setErrors(["Test error"]);
    });

    expect(result.current.id).toBe("test-id");
    expect(result.current.name).toBe("Test Schema");
    expect(result.current.description).toBe("Test Description");
    expect(result.current.errors).toEqual(["Test error"]);
  });

  test("updates fields array", () => {
    const { result } = renderHook(() =>
      useSchemaForm({
        isOpen: true,
        mode: "create",
      }),
    );

    const newFields: SchemaField[] = [
      {
        id: "new-field",
        name: "new_field",
        type: "number",
        primary_key: false,
        required: true,
      },
    ];

    act(() => {
      result.current.setFields(newFields);
    });

    expect(result.current.fields).toEqual(newFields);
  });

  test("updates indexes array", () => {
    const { result } = renderHook(() =>
      useSchemaForm({
        isOpen: true,
        mode: "create",
      }),
    );

    act(() => {
      result.current.setIndexes(["index1", "index2"]);
    });

    expect(result.current.indexes).toEqual(["index1", "index2"]);
  });

  test("trims whitespace from enum values", () => {
    const { result } = renderHook(() =>
      useSchemaForm({
        isOpen: true,
        mode: "create",
      }),
    );

    act(() => {
      result.current.handleAddEnumValue(0, "  test_value  ");
    });

    expect(result.current.fields[0].enum).toEqual(["test_value"]);
  });

  test("ignores empty enum values", () => {
    const { result } = renderHook(() =>
      useSchemaForm({
        isOpen: true,
        mode: "create",
      }),
    );

    act(() => {
      result.current.handleAddEnumValue(0, "");
      result.current.handleAddEnumValue(0, "   ");
    });

    expect(result.current.fields[0].enum).toBeUndefined();
  });

  test("handles adding index with empty newIndex", () => {
    const { result } = renderHook(() =>
      useSchemaForm({
        isOpen: true,
        mode: "create",
      }),
    );

    act(() => {
      result.current.handleAddIndex();
    });

    expect(result.current.indexes).toEqual([]);
  });

  test("resets properly when props change", () => {
    const { result, rerender } = renderHook(
      ({ isOpen, mode, schemaId, initialSchema }) =>
        useSchemaForm({
          isOpen,
          mode,
          schemaId,
          initialSchema,
        }),
      {
        initialProps: {
          isOpen: true,
          mode: "create" as const,
          schemaId: undefined,
          initialSchema: undefined,
        },
      },
    );

    expect(result.current.name).toBe("");

    rerender({
      isOpen: true,
      mode: "edit" as const,
      schemaId: "schema-1",
      initialSchema: mockSchema,
    });

    expect(result.current.name).toBe("User Schema");
    expect(result.current.id).toBe("schema-1");
  });
});
