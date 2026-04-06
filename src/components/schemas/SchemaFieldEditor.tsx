import React from "react";
import {
  Box,
  HStack,
  Field,
  Input,
  Checkbox,
  IconButton,
} from "@chakra-ui/react";
import { Trash2 } from "lucide-react";
import { SchemaField } from "../../model/schemas-table";
import SelectField from "../common/SelectField";
import { EnumValueManager } from "./EnumValueManager";
import { SCHEMA_TYPE_OPTIONS } from "../../model/schemaTypes";

interface SchemaFieldEditorProps {
  field: SchemaField;
  index: number;
  onFieldChange: (index: number, field: Partial<SchemaField>) => void;
  onRemoveField: (index: number) => void;
  onAddEnumValue: (fieldIndex: number, value: string) => void;
  onRemoveEnumValue: (fieldIndex: number, value: string) => void;
  canRemove: boolean;
  contentRef: React.RefObject<HTMLDivElement>;
}

export const SchemaFieldEditor: React.FC<SchemaFieldEditorProps> = ({
  field,
  index,
  onFieldChange,
  onRemoveField,
  onAddEnumValue,
  onRemoveEnumValue,
  canRemove,
  contentRef,
}) => {
  return (
    <Box p={4} borderWidth="1px" borderRadius="md">
      <HStack gap={4} mb={3}>
        <Field.Root required flex={1}>
          <Field.Label>
            Field Name <Field.RequiredIndicator />
          </Field.Label>
          <Input
            value={field.name}
            onChange={(e) =>
              onFieldChange(index, {
                name: e.target.value,
              })
            }
            placeholder="e.g., customer_id"
          />
        </Field.Root>

        <Box flex={1}>
          <SelectField
            label="Type"
            value={field.type ? [field.type] : []}
            onValueChange={(value) => {
              const typeValue = Array.isArray(value) ? value[0] : value;
              onFieldChange(index, {
                type: typeValue as SchemaField["type"],
              });
            }}
            items={SCHEMA_TYPE_OPTIONS}
            contentRef={contentRef}
          />
        </Box>

        <IconButton
          aria-label="Remove field"
          size="sm"
          colorPalette="red"
          variant="ghost"
          onClick={() => onRemoveField(index)}
          disabled={!canRemove}
        >
          <Trash2 size={16} />
        </IconButton>
      </HStack>

      <HStack gap={4}>
        <Checkbox.Root
          checked={field.primary_key}
          onCheckedChange={(details) =>
            onFieldChange(index, {
              primary_key: details.checked,
            })
          }
        >
          <Checkbox.HiddenInput />
          <Checkbox.Control>
            <Checkbox.Indicator />
          </Checkbox.Control>
          <Checkbox.Label>Primary Key</Checkbox.Label>
        </Checkbox.Root>

        <Checkbox.Root
          checked={field.required}
          onCheckedChange={(details) =>
            onFieldChange(index, {
              required: details.checked,
            })
          }
        >
          <Checkbox.HiddenInput />
          <Checkbox.Control>
            <Checkbox.Indicator />
          </Checkbox.Control>
          <Checkbox.Label>Required</Checkbox.Label>
        </Checkbox.Root>
      </HStack>

      {field.type === "enum" && (
        <Box mt={3}>
          <EnumValueManager
            values={field.enum || []}
            onAddValue={(value) => onAddEnumValue(index, value)}
            onRemoveValue={(value) => onRemoveEnumValue(index, value)}
          />
        </Box>
      )}
    </Box>
  );
};
