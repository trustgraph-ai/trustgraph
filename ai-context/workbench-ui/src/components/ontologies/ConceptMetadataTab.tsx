import React from "react";
import {
  VStack,
  Input,
  Text,
  Box,
  Badge,
  Wrap,
  WrapItem,
  Field,
} from "@chakra-ui/react";
import { OntologyConcept } from "@trustgraph/react-state";

interface ConceptMetadataTabProps {
  concept?: OntologyConcept;
  editedConcept: OntologyConcept;
  onUpdateField: (field: keyof OntologyConcept, value: unknown) => void;
}

export const ConceptMetadataTab: React.FC<ConceptMetadataTabProps> = ({
  concept,
  editedConcept,
  onUpdateField,
}) => {
  return (
    <VStack gap={4} align="stretch">
      <Field.Root>
        <Field.Label>Concept ID</Field.Label>
        <Input
          value={editedConcept.id}
          onChange={(e) => onUpdateField("id", e.target.value)}
          disabled={!!concept} // Don't allow editing existing IDs
        />
        {concept && (
          <Text fontSize="sm" color="fg.muted">
            ID cannot be changed for existing concepts
          </Text>
        )}
      </Field.Root>

      <Box p={4} bg="bg.muted" borderRadius="md">
        <Text fontSize="sm" fontWeight="bold" mb={2}>
          Concept Summary
        </Text>
        <Wrap>
          <WrapItem>
            <Badge colorPalette={editedConcept.prefLabel ? "primary" : "red"}>
              {editedConcept.prefLabel ? "Has Label" : "No Label"}
            </Badge>
          </WrapItem>
          <WrapItem>
            <Badge
              colorPalette={editedConcept.definition ? "primary" : "yellow"}
            >
              {editedConcept.definition ? "Defined" : "No Definition"}
            </Badge>
          </WrapItem>
          <WrapItem>
            <Badge colorPalette={editedConcept.broader ? "blue" : "gray"}>
              {editedConcept.broader ? "Has Parent" : "Root Level"}
            </Badge>
          </WrapItem>
          <WrapItem>
            <Badge>{(editedConcept.narrower || []).length} Children</Badge>
          </WrapItem>
          <WrapItem>
            <Badge>{(editedConcept.related || []).length} Related</Badge>
          </WrapItem>
        </Wrap>
      </Box>
    </VStack>
  );
};
