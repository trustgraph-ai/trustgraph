import { createColumnHelper } from "@tanstack/react-table";
import { Flex, HStack, Badge, Text, Code } from "@chakra-ui/react";

export interface SchemaField {
  id: string; // Unique identifier for React keys
  name: string;
  type: "string" | "integer" | "float" | "boolean" | "timestamp" | "enum";
  primary_key?: boolean;
  required?: boolean;
  enum?: string[];
}

export interface Schema {
  name: string;
  description: string;
  fields: SchemaField[];
  indexes?: string[];
}

export type SchemaTableRow = [string, Schema];

const columnHelper = createColumnHelper<SchemaTableRow>();

export const schemaColumns = [
  columnHelper.accessor("0", {
    header: "ID",
    cell: (info) => <Code p={2}>{info.getValue()}</Code>,
  }),
  columnHelper.accessor((row) => row[1].description, {
    id: "description",
    header: "Description",
    cell: (info) => <Text>{info.getValue()}</Text>,
  }),
  columnHelper.display({
    id: "fields",
    header: "Fields",
    cell: ({ row }) => {
      const fieldCount = row.original[1].fields.length;
      const pkCount = row.original[1].fields.filter(
        (f) => f.primary_key,
      ).length;
      return (
        <HStack gap={2}>
          <Badge size="sm" colorPalette="blue">
            {fieldCount} field{fieldCount !== 1 ? "s" : ""}
          </Badge>
          {pkCount > 0 && (
            <Badge size="sm" colorPalette="purple">
              {pkCount} PK
            </Badge>
          )}
        </HStack>
      );
    },
  }),
  columnHelper.display({
    id: "types",
    header: "Types",
    cell: ({ row }) => {
      const types = [...new Set(row.original[1].fields.map((f) => f.type))];
      return (
        <Flex wrap="wrap" gap={1}>
          {types.map((type) => (
            <Badge key={type} size="sm" variant="outline">
              {type}
            </Badge>
          ))}
        </Flex>
      );
    },
  }),
  columnHelper.display({
    id: "indexes",
    header: "Indexes",
    cell: ({ row }) => {
      const indexes = row.original[1].indexes || [];
      return (
        <Text fontSize="sm" color="gray.600">
          {indexes.length > 0 ? indexes.join(", ") : "None"}
        </Text>
      );
    },
  }),
];
