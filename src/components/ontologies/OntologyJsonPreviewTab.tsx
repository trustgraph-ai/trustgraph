import React from "react";
import { Box } from "@chakra-ui/react";
import { Ontology } from "@trustgraph/react-state";

interface OntologyJsonPreviewTabProps {
  ontology: Ontology;
}

export const OntologyJsonPreviewTab: React.FC<OntologyJsonPreviewTabProps> = ({
  ontology,
}) => {
  return (
    <Box
      as="pre"
      p={4}
      bg="bg.muted"
      borderRadius="md"
      overflow="auto"
      maxH="400px"
      fontSize="sm"
    >
      {JSON.stringify(ontology, null, 2)}
    </Box>
  );
};
