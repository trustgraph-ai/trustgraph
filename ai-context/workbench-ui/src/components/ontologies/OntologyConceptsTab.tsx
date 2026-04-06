import React from "react";
import {
  VStack,
  HStack,
  Text,
  Button,
  Box,
  IconButton,
} from "@chakra-ui/react";
import { Plus, Trash2 } from "lucide-react";
import TextField from "../common/TextField";
import TextAreaField from "../common/TextAreaField";
import { Ontology, OntologyConcept } from "@trustgraph/react-state";

interface OntologyConceptsTabProps {
  ontology: Ontology;
  onAddConcept: () => void;
  onDeleteConcept: (id: string) => void;
  onUpdateConcept: (
    id: string,
    field: keyof OntologyConcept,
    value: string,
  ) => void;
}

export const OntologyConceptsTab: React.FC<OntologyConceptsTabProps> = ({
  ontology,
  onAddConcept,
  onDeleteConcept,
  onUpdateConcept,
}) => {
  return (
    <VStack gap={4} align="stretch">
      <HStack justify="space-between">
        <Text fontSize="lg" fontWeight="bold">
          Concepts
        </Text>
        <Button colorPalette="primary" size="sm" onClick={onAddConcept}>
          <Plus /> Add Concept
        </Button>
      </HStack>

      {Object.entries(ontology.concepts).length === 0 ? (
        <Box p={4} borderWidth="1px" borderRadius="md" bg="bg.muted">
          <Text color="fg.muted">
            No concepts yet. Click "Add Concept" to create one.
          </Text>
        </Box>
      ) : (
        <VStack gap={4} align="stretch">
          {Object.entries(ontology.concepts).map(([id, concept]) => (
            <Box key={id} p={4} borderWidth="1px" borderRadius="md">
              <HStack justify="space-between" mb={3}>
                <Text fontWeight="bold">{concept.prefLabel}</Text>
                <IconButton
                  aria-label="Delete concept"
                  size="sm"
                  colorPalette="red"
                  variant="ghost"
                  onClick={() => onDeleteConcept(id)}
                >
                  <Trash2 />
                </IconButton>
              </HStack>
              <VStack gap={2} align="stretch">
                <TextField
                  label="Preferred Label"
                  value={concept.prefLabel}
                  onValueChange={(value) =>
                    onUpdateConcept(id, "prefLabel", value)
                  }
                />
                <TextAreaField
                  label="Definition"
                  value={concept.definition || ""}
                  onValueChange={(value) =>
                    onUpdateConcept(id, "definition", value)
                  }
                />
              </VStack>
            </Box>
          ))}
        </VStack>
      )}
    </VStack>
  );
};
