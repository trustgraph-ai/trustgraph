import React from "react";
import { VStack } from "@chakra-ui/react";
import SelectField from "../common/SelectField";
import { ArrayFieldEditor } from "./ArrayFieldEditor";
import { OntologyConcept } from "@trustgraph/react-state";

interface ConceptRelationshipsTabProps {
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

export const ConceptRelationshipsTab: React.FC<
  ConceptRelationshipsTabProps
> = ({
  editedConcept,
  availableConcepts,
  onUpdateField,
  onAddItem,
  onRemoveItem,
  onUpdateItem,
}) => {
  return (
    <VStack gap={4} align="stretch">
      <SelectField
        label="Broader Concept"
        items={[
          {
            value: "",
            label: "No parent concept",
            description: "No parent concept",
          },
          ...availableConcepts.map((c) => ({
            value: c.id,
            label: c.prefLabel,
            description: c.prefLabel,
          })),
        ]}
        value={[editedConcept.broader || ""]}
        onValueChange={(values) => {
          const value = values[0] || "";
          onUpdateField("broader", value === "" ? null : value);
        }}
      />

      <ArrayFieldEditor
        label="Narrower Concepts"
        field="narrower"
        placeholder=""
        isConceptSelect={true}
        items={(editedConcept.narrower as string[]) || []}
        availableConcepts={availableConcepts}
        onAddItem={onAddItem}
        onRemoveItem={onRemoveItem}
        onUpdateItem={onUpdateItem}
      />

      <ArrayFieldEditor
        label="Related Concepts"
        field="related"
        placeholder=""
        isConceptSelect={true}
        items={(editedConcept.related as string[]) || []}
        availableConcepts={availableConcepts}
        onAddItem={onAddItem}
        onRemoveItem={onRemoveItem}
        onUpdateItem={onUpdateItem}
      />
    </VStack>
  );
};
