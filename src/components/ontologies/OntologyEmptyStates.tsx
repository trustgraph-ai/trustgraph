import React from "react";
import { Box, VStack, Text } from "@chakra-ui/react";
import SelectField from "../common/SelectField";
import { Ontology } from "@trustgraph/react-state";

interface EmptyStatesProps {
  type: "no-ontologies" | "no-ontology-selected" | "no-concept-selected";
  ontologies?: Array<[string, Ontology]>;
  onOntologyChange?: (ontologyId: string) => void;
}

export const OntologyEmptyStates: React.FC<EmptyStatesProps> = ({
  type,
  ontologies,
  onOntologyChange,
}) => {
  if (type === "no-ontologies") {
    return (
      <Box p={8} textAlign="center" color="fg.muted">
        <Text mb={4}>No ontologies available. Create one to get started.</Text>
      </Box>
    );
  }

  if (type === "no-ontology-selected") {
    return (
      <VStack gap={4} p={8}>
        <Text color="fg.muted">Select a ontology to start editing:</Text>
        <Box maxW="400px">
          <SelectField
            label="Select Ontology"
            items={(ontologies || []).map(([id, ontology]) => ({
              value: id,
              label: ontology.metadata.name,
              description: ontology.metadata.name,
            }))}
            value={[]}
            onValueChange={(values) => {
              if (values.length > 0 && onOntologyChange) {
                onOntologyChange(values[0]);
              }
            }}
          />
        </Box>
      </VStack>
    );
  }

  if (type === "no-concept-selected") {
    return (
      <Box p={8} textAlign="center" color="fg.muted">
        <Text>
          Select a concept from the tree to view details, or create a new
          concept.
        </Text>
      </Box>
    );
  }

  return null;
};
