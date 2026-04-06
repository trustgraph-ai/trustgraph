import { SchemaField } from "../model/schemas-table";

export interface SchemaTypeOption {
  value: SchemaField["type"];
  label: string;
  description: string;
}

export const SCHEMA_TYPE_OPTIONS: SchemaTypeOption[] = [
  {
    value: "string",
    label: "String",
    description: "Text data of variable length",
  },
  {
    value: "integer",
    label: "Integer",
    description: "Whole numbers (e.g., 1, 42, -10)",
  },
  {
    value: "float",
    label: "Float",
    description: "Decimal numbers (e.g., 3.14, -2.5)",
  },
  {
    value: "boolean",
    label: "Boolean",
    description: "True or false values",
  },
  {
    value: "timestamp",
    label: "Timestamp",
    description: "Date and time values",
  },
  {
    value: "enum",
    label: "Enum",
    description: "Predefined set of allowed values",
  },
];

export const DEFAULT_FIELD: Omit<SchemaField, "id"> = {
  name: "",
  type: "string",
  primary_key: false,
  required: false,
};
