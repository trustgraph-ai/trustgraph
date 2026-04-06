import React from "react";
import { Box, Text, IconButton } from "@chakra-ui/react";
import { Plus } from "lucide-react";

interface OntologyTreeEmptyProps {
  onAddConcept: () => void;
}

export const OntologyTreeEmpty: React.FC<OntologyTreeEmptyProps> = ({
  onAddConcept,
}) => {
  return (
    <Box p={4} textAlign="center" color="fg.muted">
      <Text mb={4}>No concepts in this ontology yet.</Text>
      <IconButton
        aria-label="Add first concept"
        colorPalette="primary"
        onClick={onAddConcept}
      >
        <Plus />
      </IconButton>
      <Text fontSize="sm" mt={2}>
        Add your first concept
      </Text>
    </Box>
  );
};
