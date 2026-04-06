import { useState, useEffect } from "react";
import { v4 as uuidv4 } from "uuid";
import { Schema, SchemaField } from "../../model/schemas-table";
import { DEFAULT_FIELD } from "../../model/schemaTypes";

interface UseSchemaFormProps {
  isOpen: boolean;
  mode: "create" | "edit";
  schemaId?: string;
  initialSchema?: Schema;
}

export const useSchemaForm = ({
  isOpen,
  schemaId,
  initialSchema,
}: Omit<UseSchemaFormProps, "mode">) => {
  const [id, setId] = useState(schemaId || "");
  const [name, setName] = useState(initialSchema?.name || "");
  const [description, setDescription] = useState(
    initialSchema?.description || "",
  );
  const [fields, setFields] = useState<SchemaField[]>(
    initialSchema?.fields?.map((field) => ({
      ...field,
      id: field.id || uuidv4(),
    })) || [
      {
        ...DEFAULT_FIELD,
        id: uuidv4(),
      },
    ],
  );
  const [indexes, setIndexes] = useState<string[]>(
    initialSchema?.indexes || [],
  );
  const [newIndex, setNewIndex] = useState("");
  const [errors, setErrors] = useState<string[]>([]);

  // Reset state when props change
  useEffect(() => {
    if (isOpen) {
      setId(schemaId || "");
      setName(initialSchema?.name || "");
      setDescription(initialSchema?.description || "");
      setFields(
        initialSchema?.fields?.map((field) => ({
          ...field,
          id: field.id || uuidv4(),
        })) || [
          {
            id: uuidv4(),
            name: "",
            type: "string",
            primary_key: false,
            required: false,
          },
        ],
      );
      setIndexes(initialSchema?.indexes || []);
    }
  }, [isOpen, schemaId, initialSchema]);

  const handleAddField = () => {
    setFields([
      ...fields,
      {
        ...DEFAULT_FIELD,
        id: uuidv4(),
      },
    ]);
  };

  const handleRemoveField = (index: number) => {
    const newFields = fields.filter((_, i) => i !== index);
    setFields(newFields);
    // Remove field from indexes if it exists
    const removedFieldName = fields[index].name;
    setIndexes(indexes.filter((idx) => idx !== removedFieldName));
  };

  const handleFieldChange = (index: number, field: Partial<SchemaField>) => {
    const newFields = [...fields];
    newFields[index] = { ...newFields[index], ...field };

    // Clear enum values if type is not enum
    if (field.type && field.type !== "enum") {
      delete newFields[index].enum;
    }

    setFields(newFields);
  };

  const handleAddIndex = () => {
    if (newIndex && !indexes.includes(newIndex)) {
      setIndexes([...indexes, newIndex]);
      setNewIndex("");
    }
  };

  const handleRemoveIndex = (index: string) => {
    setIndexes(indexes.filter((idx) => idx !== index));
  };

  const handleAddEnumValue = (fieldIndex: number, value: string) => {
    if (value.trim()) {
      const field = fields[fieldIndex];
      const enumValues = field.enum || [];
      if (!enumValues.includes(value.trim())) {
        handleFieldChange(fieldIndex, {
          enum: [...enumValues, value.trim()],
        });
      }
    }
  };

  const handleRemoveEnumValue = (fieldIndex: number, value: string) => {
    const field = fields[fieldIndex];
    const enumValues = field.enum || [];
    handleFieldChange(fieldIndex, {
      enum: enumValues.filter((v) => v !== value),
    });
  };

  const resetForm = () => {
    setId("");
    setName("");
    setDescription("");
    setFields([
      {
        ...DEFAULT_FIELD,
        id: uuidv4(),
      },
    ]);
    setIndexes([]);
    setErrors([]);
  };

  const getSchema = (): Schema => ({
    name,
    description,
    fields,
    indexes: indexes.length > 0 ? indexes : undefined,
  });

  return {
    // Form state
    id,
    setId,
    name,
    setName,
    description,
    setDescription,
    fields,
    setFields,
    indexes,
    setIndexes,
    newIndex,
    setNewIndex,
    errors,
    setErrors,

    // Field handlers
    handleAddField,
    handleRemoveField,
    handleFieldChange,
    handleAddEnumValue,
    handleRemoveEnumValue,

    // Index handlers
    handleAddIndex,
    handleRemoveIndex,

    // Utility functions
    resetForm,
    getSchema,
  };
};
