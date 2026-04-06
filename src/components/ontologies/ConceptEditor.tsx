import React, { useState, useEffect } from "react";
import { Box, VStack, Tabs } from "@chakra-ui/react";
import { useNotification } from "@trustgraph/react-state";
import { OntologyConcept, Ontology } from "@trustgraph/react-state";
import TextAreaField from "../common/TextAreaField";
import { ConceptEditorHeader } from "./ConceptEditorHeader";
import { ConceptMetadataTab } from "./ConceptMetadataTab";
import { ConceptBasicTab } from "./ConceptBasicTab";
import { ConceptRelationshipsTab } from "./ConceptRelationshipsTab";
import { ArrayFieldEditor } from "./ArrayFieldEditor";

interface ConceptEditorProps {
  concept?: OntologyConcept;
  ontology: Ontology;
  onSave: (concept: OntologyConcept) => void;
  onCancel: () => void;
}

export const ConceptEditor: React.FC<ConceptEditorProps> = ({
  concept,
  ontology,
  onSave,
  onCancel,
}) => {
  const notify = useNotification();
  const [editedConcept, setEditedConcept] = useState<OntologyConcept>(
    concept || {
      id: `concept-${Date.now()}`,
      prefLabel: "",
      narrower: [],
      related: [],
    },
  );

  useEffect(() => {
    if (concept) {
      setEditedConcept(concept);
    }
  }, [concept]);

  const handleSave = () => {
    if (!editedConcept.prefLabel.trim()) {
      notify.error("Preferred label is required");
      return;
    }

    onSave(editedConcept);
  };

  const updateField = (field: keyof OntologyConcept, value: unknown) => {
    setEditedConcept((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const addToArrayField = (field: keyof OntologyConcept, value: string) => {
    const currentArray = (editedConcept[field] as string[]) || [];
    updateField(field, [...currentArray, value]);
  };

  const removeFromArrayField = (
    field: keyof OntologyConcept,
    index: number,
  ) => {
    const currentArray = (editedConcept[field] as string[]) || [];
    updateField(
      field,
      currentArray.filter((_, i) => i !== index),
    );
  };

  const updateArrayItem = (
    field: keyof OntologyConcept,
    index: number,
    value: string,
  ) => {
    const currentArray = (editedConcept[field] as string[]) || [];
    const newArray = [...currentArray];
    newArray[index] = value;
    updateField(field, newArray);
  };

  const availableConcepts = Object.values(ontology.concepts)
    .filter((c) => c.id !== editedConcept.id)
    .sort((a, b) => a.prefLabel.localeCompare(b.prefLabel));

  return (
    <VStack gap={4} align="stretch" h="100%">
      <ConceptEditorHeader
        concept={concept}
        onSave={handleSave}
        onCancel={onCancel}
      />

      <Box flex="1" overflowY="auto">
        <Tabs.Root defaultValue="basic">
          <Tabs.List>
            <Tabs.Trigger value="basic">Basic Info</Tabs.Trigger>
            <Tabs.Trigger value="definition">Definition</Tabs.Trigger>
            <Tabs.Trigger value="examples">Examples</Tabs.Trigger>
            <Tabs.Trigger value="relationships">Relationships</Tabs.Trigger>
            <Tabs.Trigger value="metadata">Metadata</Tabs.Trigger>
          </Tabs.List>

          <Tabs.Content value="basic">
            <ConceptBasicTab
              editedConcept={editedConcept}
              availableConcepts={availableConcepts}
              onUpdateField={updateField}
              onAddItem={addToArrayField}
              onRemoveItem={removeFromArrayField}
              onUpdateItem={updateArrayItem}
            />
          </Tabs.Content>

          <Tabs.Content value="definition">
            <VStack gap={4} align="stretch">
              <TextAreaField
                label="Definition"
                value={editedConcept.definition || ""}
                onValueChange={(value) => updateField("definition", value)}
                placeholder="Formal definition of this concept..."
              />

              <TextAreaField
                label="Scope Note"
                value={editedConcept.scopeNote || ""}
                onValueChange={(value) => updateField("scopeNote", value)}
                placeholder="Additional context about the scope and usage..."
              />
            </VStack>
          </Tabs.Content>

          <Tabs.Content value="examples">
            <ArrayFieldEditor
              label="Examples"
              field="example"
              placeholder="Add example..."
              items={(editedConcept.example as string[]) || []}
              availableConcepts={availableConcepts}
              onAddItem={addToArrayField}
              onRemoveItem={removeFromArrayField}
              onUpdateItem={updateArrayItem}
            />
          </Tabs.Content>

          <Tabs.Content value="relationships">
            <ConceptRelationshipsTab
              editedConcept={editedConcept}
              availableConcepts={availableConcepts}
              onUpdateField={updateField}
              onAddItem={addToArrayField}
              onRemoveItem={removeFromArrayField}
              onUpdateItem={updateArrayItem}
            />
          </Tabs.Content>

          <Tabs.Content value="metadata">
            <ConceptMetadataTab
              concept={concept}
              editedConcept={editedConcept}
              onUpdateField={updateField}
            />
          </Tabs.Content>
        </Tabs.Root>
      </Box>
    </VStack>
  );
};
