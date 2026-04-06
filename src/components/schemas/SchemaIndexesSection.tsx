import React from "react";
import {
  Box,
  Text,
  HStack,
  Button,
  Badge,
  Flex,
  CloseButton,
} from "@chakra-ui/react";
import { SchemaField } from "../../model/schemas-table";
import SelectField from "../common/SelectField";

interface SchemaIndexesSectionProps {
  indexes: string[];
  fields: SchemaField[];
  newIndex: string;
  onNewIndexChange: (value: string) => void;
  onAddIndex: () => void;
  onRemoveIndex: (index: string) => void;
  contentRef: React.RefObject<HTMLDivElement>;
}

export const SchemaIndexesSection: React.FC<SchemaIndexesSectionProps> = ({
  indexes,
  fields,
  newIndex,
  onNewIndexChange,
  onAddIndex,
  onRemoveIndex,
  contentRef,
}) => {
  const availableFields = fields.filter(
    (f) =>
      f.name &&
      f.name.trim() !== "" &&
      !f.primary_key &&
      !indexes.includes(f.name),
  );

  return (
    <Box>
      <Text fontSize="lg" fontWeight="bold" mb={4}>
        Indexes
      </Text>

      {availableFields.length === 0 ? (
        <Text fontSize="sm" color="fg.muted">
          No fields available for indexing. Add field names first.
        </Text>
      ) : (
        <HStack mb={2}>
          <Box flex={1}>
            <SelectField
              label=""
              value={newIndex ? [newIndex] : []}
              onValueChange={(value) => {
                const indexValue = Array.isArray(value) ? value[0] : value;
                onNewIndexChange(indexValue || "");
              }}
              items={availableFields.map((field) => ({
                value: field.name,
                label: field.name,
                description: field.name,
              }))}
              contentRef={contentRef}
            />
          </Box>
          <Button
            onClick={onAddIndex}
            colorPalette="primary"
            disabled={!newIndex}
            mt={8}
          >
            Add Index
          </Button>
        </HStack>
      )}

      <Flex wrap="wrap" gap={2}>
        {indexes.map((index) => (
          <Badge
            key={index}
            colorPalette="green"
            borderRadius="full"
            px={3}
            py={1}
            display="flex"
            alignItems="center"
            gap={2}
          >
            {index}
            <CloseButton size="sm" onClick={() => onRemoveIndex(index)} />
          </Badge>
        ))}
      </Flex>
    </Box>
  );
};
