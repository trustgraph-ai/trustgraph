import React, { useState } from "react";
import {
  Box,
  VStack,
  HStack,
  Field,
  Input,
  IconButton,
  Text,
} from "@chakra-ui/react";
import { Plus, X } from "lucide-react";
import SelectField from "../common/SelectField";
import { OntologyConcept } from "@trustgraph/react-state";

interface ArrayFieldEditorProps {
  label: string;
  field: keyof OntologyConcept;
  placeholder: string;
  isConceptSelect?: boolean;
  items: string[];
  availableConcepts: Array<{ id: string; prefLabel: string }>;
  onAddItem: (field: keyof OntologyConcept, value: string) => void;
  onRemoveItem: (field: keyof OntologyConcept, index: number) => void;
  onUpdateItem: (
    field: keyof OntologyConcept,
    index: number,
    value: string,
  ) => void;
}

export const ArrayFieldEditor: React.FC<ArrayFieldEditorProps> = ({
  label,
  field,
  placeholder,
  isConceptSelect = false,
  items,
  availableConcepts,
  onAddItem,
  onRemoveItem,
  onUpdateItem,
}) => {
  const [newItem, setNewItem] = useState("");

  const handleAdd = () => {
    const itemValue = String(newItem || "").trim();
    if (itemValue && !items.includes(itemValue)) {
      onAddItem(field, itemValue);
      setNewItem("");
    }
  };

  // If this is a concept select but there are no available concepts, show a message
  if (isConceptSelect && availableConcepts.length === 0) {
    return (
      <Field.Root>
        <Field.Label>{label}</Field.Label>
        <Text fontSize="sm" color="fg.muted">
          No other concepts available. Create more concepts in this ontology to
          establish relationships.
        </Text>
      </Field.Root>
    );
  }

  return (
    <Field.Root>
      <Field.Label>{label}</Field.Label>
      <VStack align="stretch" gap={2}>
        {items.map((item, index) => (
          <HStack key={index}>
            {isConceptSelect ? (
              <Box flex="1" minW="300px">
                <SelectField
                  label="Concept"
                  items={[
                    {
                      value: "",
                      label: "Select concept...",
                      description: "Select concept...",
                    },
                    ...availableConcepts.map((c) => ({
                      value: c.id,
                      label: c.prefLabel,
                      description: c.prefLabel,
                    })),
                  ]}
                  value={[item || ""]}
                  onValueChange={(values) =>
                    onUpdateItem(field, index, values[0] || "")
                  }
                />
              </Box>
            ) : (
              <Input
                value={item}
                onChange={(e) => onUpdateItem(field, index, e.target.value)}
                flex="1"
              />
            )}
            <IconButton
              aria-label="Remove"
              size="sm"
              variant="ghost"
              colorPalette="red"
              onClick={() => onRemoveItem(field, index)}
            >
              <X />
            </IconButton>
          </HStack>
        ))}

        {/* Only show Add section if there are concepts available */}
        {(!isConceptSelect ||
          availableConcepts.filter((c) => !items.includes(c.id)).length >
            0) && (
          <HStack>
            {isConceptSelect ? (
              <Box flex="1" minW="300px">
                <SelectField
                  label="Add Concept"
                  items={availableConcepts
                    .filter((c) => !items.includes(c.id))
                    .map((c) => ({
                      value: c.id,
                      label: c.prefLabel,
                      description: c.prefLabel,
                    }))}
                  value={newItem ? [newItem] : []}
                  onValueChange={(values) =>
                    setNewItem(values.length > 0 ? values[0] : "")
                  }
                />
              </Box>
            ) : (
              <Input
                value={newItem}
                onChange={(e) => setNewItem(e.target.value)}
                placeholder={placeholder}
                onKeyPress={(e) => e.key === "Enter" && handleAdd()}
              />
            )}
            <IconButton
              aria-label="Add"
              size="sm"
              variant="outline"
              colorPalette="primary"
              onClick={handleAdd}
              disabled={
                !String(newItem || "").trim() ||
                (isConceptSelect
                  ? items.includes(String(newItem || ""))
                  : false)
              }
            >
              <Plus />
            </IconButton>
          </HStack>
        )}
      </VStack>
    </Field.Root>
  );
};
