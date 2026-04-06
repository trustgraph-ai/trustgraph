import { Schema, SchemaTableRow } from "../model/schemas-table";

export const validateSchema = (
  schema: Schema,
  existingSchemas: SchemaTableRow[],
  newSchemaId?: string,
): string[] => {
  const errors: string[] = [];

  // Check if schema ID is provided for new schemas
  if (newSchemaId !== undefined) {
    if (!newSchemaId.trim()) {
      errors.push("Schema ID is required");
    } else if (existingSchemas.some(([id]) => id === newSchemaId)) {
      errors.push(`Schema with ID "${newSchemaId}" already exists`);
    }
  }

  // Check if name is provided
  if (!schema.name.trim()) {
    errors.push("Schema name is required");
  }

  // Check if description is provided
  if (!schema.description.trim()) {
    errors.push("Schema description is required");
  }

  // Check if at least one field exists
  if (schema.fields.length === 0) {
    errors.push("At least one field is required");
  }

  // Check for duplicate field names
  const fieldNames = schema.fields.map((f) => f.name);
  const duplicateFields = fieldNames.filter(
    (name, index) => fieldNames.indexOf(name) !== index,
  );
  if (duplicateFields.length > 0) {
    errors.push(`Duplicate field names: ${duplicateFields.join(", ")}`);
  }

  // Check if all fields have names
  schema.fields.forEach((field, index) => {
    if (!field.name.trim()) {
      errors.push(`Field ${index + 1} must have a name`);
    }
  });

  // Check if at least one primary key field exists
  const hasPrimaryKey = schema.fields.some((f) => f.primary_key);
  if (!hasPrimaryKey) {
    errors.push("At least one primary key field is required");
  }

  // Check enum fields have values
  schema.fields.forEach((field) => {
    if (field.type === "enum") {
      if (!field.enum || field.enum.length === 0) {
        errors.push(`Enum field "${field.name}" must have at least one value`);
      }
    }
  });

  // Check that indexed fields exist
  if (schema.indexes) {
    schema.indexes.forEach((indexField) => {
      if (!fieldNames.includes(indexField)) {
        errors.push(`Indexed field "${indexField}" does not exist`);
      }
    });
  }

  return errors;
};
