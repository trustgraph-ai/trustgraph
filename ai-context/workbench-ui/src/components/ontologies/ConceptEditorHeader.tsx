import React from "react";
import { HStack, Text, Button } from "@chakra-ui/react";
import { Save } from "lucide-react";
import { OntologyConcept } from "@trustgraph/react-state";

interface ConceptEditorHeaderProps {
  concept?: OntologyConcept;
  onSave: () => void;
  onCancel: () => void;
}

export const ConceptEditorHeader: React.FC<ConceptEditorHeaderProps> = ({
  concept,
  onSave,
  onCancel,
}) => {
  return (
    <HStack justify="space-between" align="center">
      <Text fontSize="lg" fontWeight="bold">
        {concept ? "Edit Concept" : "New Concept"}
      </Text>
      <HStack>
        <Button variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button colorPalette="primary" onClick={onSave}>
          <Save /> Save
        </Button>
      </HStack>
    </HStack>
  );
};
