import React from "react";
import { VStack } from "@chakra-ui/react";
import TextField from "../common/TextField";
import { Ontology } from "@trustgraph/react-state";

interface OntologySchemeTabProps {
  ontology: Ontology;
  onSchemeChange: (field: keyof Ontology["scheme"], value: string) => void;
}

export const OntologySchemeTab: React.FC<OntologySchemeTabProps> = ({
  ontology,
  onSchemeChange,
}) => {
  return (
    <VStack gap={4} align="stretch">
      <TextField
        label="Scheme URI"
        value={ontology.scheme.uri}
        onValueChange={(value) => onSchemeChange("uri", value)}
        placeholder="Will be auto-generated if empty"
      />

      <TextField
        label="Scheme Label"
        value={ontology.scheme.prefLabel}
        onValueChange={(value) => onSchemeChange("prefLabel", value)}
        placeholder="Will use ontology name if empty"
      />
    </VStack>
  );
};
