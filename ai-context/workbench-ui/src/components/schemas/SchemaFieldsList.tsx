import React from "react";
import { Box, VStack, HStack, Text, Button } from "@chakra-ui/react";
import { Plus } from "lucide-react";
import { SchemaField } from "../../model/schemas-table";
import { SchemaFieldEditor } from "./SchemaFieldEditor";

interface SchemaFieldsListProps {
  fields: SchemaField[];
  onFieldChange: (index: number, field: Partial<SchemaField>) => void;
  onAddField: () => void;
  onRemoveField: (index: number) => void;
  onAddEnumValue: (fieldIndex: number, value: string) => void;
  onRemoveEnumValue: (fieldIndex: number, value: string) => void;
  contentRef: React.RefObject<HTMLDivElement>;
}

export const SchemaFieldsList: React.FC<SchemaFieldsListProps> = ({
  fields,
  onFieldChange,
  onAddField,
  onRemoveField,
  onAddEnumValue,
  onRemoveEnumValue,
  contentRef,
}) => {
  return (
    <Box>
      <HStack justify="space-between" mb={4}>
        <Text fontSize="lg" fontWeight="bold">
          Fields
        </Text>
        <Button size="sm" colorPalette="primary" onClick={onAddField}>
          <Plus size={16} />
          Add Field
        </Button>
      </HStack>

      <VStack gap={4} align="stretch">
        {fields.map((field, index) => (
          <SchemaFieldEditor
            key={field.id}
            field={field}
            index={index}
            onFieldChange={onFieldChange}
            onRemoveField={onRemoveField}
            onAddEnumValue={onAddEnumValue}
            onRemoveEnumValue={onRemoveEnumValue}
            canRemove={fields.length > 1}
            contentRef={contentRef}
          />
        ))}
      </VStack>
    </Box>
  );
};
