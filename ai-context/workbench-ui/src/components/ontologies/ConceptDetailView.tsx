import React from "react";
import { Box, VStack, HStack, Text, Button, Heading } from "@chakra-ui/react";
import { OntologyConcept } from "@trustgraph/react-state";

interface ConceptDetailViewProps {
  concept: OntologyConcept;
  onEdit: () => void;
}

export const ConceptDetailView: React.FC<ConceptDetailViewProps> = ({
  concept,
  onEdit,
}) => {
  return (
    <VStack gap={4} align="stretch">
      <HStack justify="space-between">
        <Heading size="md">{concept.prefLabel}</Heading>
        <Button size="sm" colorPalette="primary" onClick={onEdit}>
          Edit
        </Button>
      </HStack>

      <Box p={4} borderWidth="1px" borderRadius="md" bg="bg.muted">
        <VStack align="start" gap={3}>
          {concept.definition && (
            <Box>
              <Text fontSize="sm" fontWeight="bold" color="fg.muted">
                Definition
              </Text>
              <Text>{concept.definition}</Text>
            </Box>
          )}

          {concept.scopeNote && (
            <Box>
              <Text fontSize="sm" fontWeight="bold" color="fg.muted">
                Scope Note
              </Text>
              <Text fontSize="sm">{concept.scopeNote}</Text>
            </Box>
          )}

          {concept.example && concept.example.length > 0 && (
            <Box>
              <Text fontSize="sm" fontWeight="bold" color="fg.muted">
                Examples
              </Text>
              <VStack align="start" gap={1}>
                {concept.example.map((ex, index) => (
                  <Text key={index} fontSize="sm">
                    • {ex}
                  </Text>
                ))}
              </VStack>
            </Box>
          )}
        </VStack>
      </Box>
    </VStack>
  );
};
