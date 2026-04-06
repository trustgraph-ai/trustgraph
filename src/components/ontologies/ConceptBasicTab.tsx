import React from "react";
import { VStack } from "@chakra-ui/react";
import TextField from "../common/TextField";
import { ArrayFieldEditor } from "./ArrayFieldEditor";
import { OntologyConcept } from "@trustgraph/react-state";

interface ConceptBasicTabProps {
  editedConcept: OntologyConcept;
  availableConcepts: Array<{ id: string; prefLabel: string }>;
  onUpdateField: (field: keyof OntologyConcept, value: unknown) => void;
  onAddItem: (field: keyof OntologyConcept, value: string) => void;
  onRemoveItem: (field: keyof OntologyConcept, index: number) => void;
  onUpdateItem: (
    field: keyof OntologyConcept,
    index: number,
    value: string,
  ) => void;
}

export const ConceptBasicTab: React.FC<ConceptBasicTabProps> = ({
  editedConcept,
  availableConcepts,
  onUpdateField,
  onAddItem,
  onRemoveItem,
  onUpdateItem,
}) => {
  return (
    <VStack gap={4} align="stretch">
      <TextField
        label="Preferred Label"
        value={editedConcept.prefLabel}
        onValueChange={(value) => onUpdateField("prefLabel", value)}
        placeholder="Main name for this concept"
        required
      />
      <ArrayFieldEditor
        label="Alternative Labels"
        field="altLabel"
        placeholder="Add alternative label..."
        items={(editedConcept.altLabel as string[]) || []}
        availableConcepts={availableConcepts}
        onAddItem={onAddItem}
        onRemoveItem={onRemoveItem}
        onUpdateItem={onUpdateItem}
      />
    </VStack>
  );
};
