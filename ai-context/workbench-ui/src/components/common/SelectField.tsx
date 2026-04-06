/*
 * CRITICAL: DO NOT MODIFY THIS COMPONENT WITHOUT DESIGN AUTHORITY APPROVAL
 *
 * This SelectField component is used throughout the application by 15+ components
 * across multiple domains (ontologies, flows, documents, etc.). Any changes to
 * this component's interface or behavior will have extensive downstream impact.
 *
 * Changes to this component in September 2025 broke multiple features and required
 * systematic updates across the entire application. Always prefer adapter patterns
 * or feature-specific solutions over modifying this shared infrastructure.
 *
 * Required API contract:
 * - value: string[] (arrays only)
 * - onValueChange: (values: string[]) => void
 * - items must include description fields with SelectOptionText/SelectOption
 */

import React, { useMemo } from "react";
import {
  Field,
  Select,
  Portal,
  Stack,
  createListCollection,
} from "@chakra-ui/react";

export interface SelectFieldValue {
  value: string;
  label: string;
  description?: string | React.ReactElement;
}

interface SelectFieldProps {
  label: string;

  items: SelectFieldValue[];

  value: string[];
  onValueChange: (x: string[]) => void;

  contentRef?;
}

const SelectField: React.FC<SelectFieldProps> = ({
  label,
  items,
  value,
  onValueChange,
  contentRef,
}) => {
  // Only create new collection when items actually change
  const collection = useMemo(
    () => createListCollection({ items: items }),
    [items],
  );

  return (
    <Field.Root mb={4}>
      <Field.Label fontWeight="medium">{label}</Field.Label>

      <Select.Root
        collection={collection}
        value={value}
        onValueChange={(e) => onValueChange(e.value)}
      >
        <Select.HiddenSelect />
        <Select.Control>
          <Select.Trigger>
            <Select.ValueText placeholder={label} />
          </Select.Trigger>
          <Select.IndicatorGroup>
            <Select.Indicator />
          </Select.IndicatorGroup>
        </Select.Control>
        <Portal container={contentRef}>
          <Select.Positioner>
            <Select.Content>
              {items.map((v) => (
                <Select.Item item={v.value} key={v.value}>
                  <Stack>{v.description && v.description}</Stack>
                  <Select.ItemIndicator />
                </Select.Item>
              ))}
            </Select.Content>
          </Select.Positioner>
        </Portal>
      </Select.Root>
    </Field.Root>
  );
};

export default SelectField;
