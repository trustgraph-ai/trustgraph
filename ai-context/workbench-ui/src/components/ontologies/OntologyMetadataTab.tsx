import React from "react";
import { VStack } from "@chakra-ui/react";
import TextField from "../common/TextField";
import TextAreaField from "../common/TextAreaField";
import { Ontology } from "@trustgraph/react-state";

interface OntologyMetadataTabProps {
  ontologyId: string;
  ontology: Ontology;
  mode: "create" | "edit";
  onOntologyIdChange: (value: string) => void;
  onMetadataChange: (field: keyof Ontology["metadata"], value: string) => void;
}

export const OntologyMetadataTab: React.FC<OntologyMetadataTabProps> = ({
  ontologyId,
  ontology,
  mode,
  onOntologyIdChange,
  onMetadataChange,
}) => {
  return (
    <VStack gap={4} align="stretch">
      <TextField
        label="Ontology ID"
        value={ontologyId}
        onValueChange={onOntologyIdChange}
        placeholder="e.g., risk-categories"
        required
        disabled={mode === "edit"}
      />

      <TextField
        label="Name"
        value={ontology.metadata.name}
        onValueChange={(value) => onMetadataChange("name", value)}
        placeholder="e.g., Risk Categories"
        required
      />

      <TextAreaField
        label="Description"
        value={ontology.metadata.description}
        onValueChange={(value) => onMetadataChange("description", value)}
        placeholder="Describe the purpose of this ontology"
      />

      <TextField
        label="Version"
        value={ontology.metadata.version}
        onValueChange={(value) => onMetadataChange("version", value)}
      />

      <TextField
        label="Namespace"
        value={ontology.metadata.namespace}
        onValueChange={(value) => onMetadataChange("namespace", value)}
        placeholder="http://example.org/ontologies/"
      />
    </VStack>
  );
};
