import React from "react";
import {
  Box,
  Heading,
  HStack,
  VStack,
  Button,
  IconButton,
  Text,
  Separator,
} from "@chakra-ui/react";
import { Plus, Download, Upload, Settings } from "lucide-react";
import SelectField from "../common/SelectField";
import { Ontology, OntologyConcept } from "@trustgraph/react-state";

interface OntologyManagerHeaderProps {
  currentOntology: Ontology;
  currentOntologyId: string | null;
  selectedConcept?: OntologyConcept;
  ontologies: Array<[string, Ontology]>;
  conceptBreadcrumb: string[];
  onOntologyChange: (ontologyId: string) => void;
  onConceptAdd: () => void;
  onImport: () => void;
  onExport: () => void;
  onSettings: () => void;
}

export const OntologyManagerHeader: React.FC<OntologyManagerHeaderProps> = ({
  currentOntology,
  currentOntologyId,
  selectedConcept,
  ontologies,
  conceptBreadcrumb,
  onOntologyChange,
  onConceptAdd,
  onImport,
  onExport,
  onSettings,
}) => {
  return (
    <>
      <HStack justify="space-between" align="center">
        <VStack align="start" gap={1}>
          <HStack>
            <Heading size="lg">{currentOntology.metadata.name}</Heading>
            <Text color="fg.muted">
              ({Object.keys(currentOntology.concepts).length} concepts)
            </Text>
          </HStack>
          {selectedConcept && (
            <Text fontSize="sm" color="fg.muted">
              {currentOntology.metadata.name} → {conceptBreadcrumb.join(" → ")}
            </Text>
          )}
        </VStack>

        <HStack>
          <Box w="250px">
            <SelectField
              label="Current Ontology"
              items={ontologies.map(([id, ontology]) => ({
                value: id,
                label: ontology.metadata.name,
                description: ontology.metadata.name,
              }))}
              value={currentOntologyId ? [currentOntologyId] : []}
              onValueChange={(values) => {
                if (values.length > 0) {
                  onOntologyChange(values[0]);
                }
              }}
            />
          </Box>
          <Button colorPalette="primary" onClick={onConceptAdd}>
            <Plus /> Add Concept
          </Button>
          <IconButton aria-label="Import" variant="outline" onClick={onImport}>
            <Upload />
          </IconButton>
          <IconButton aria-label="Export" variant="outline" onClick={onExport}>
            <Download />
          </IconButton>
          <IconButton
            aria-label="Settings"
            variant="outline"
            onClick={onSettings}
          >
            <Settings />
          </IconButton>
        </HStack>
      </HStack>

      <Separator />
    </>
  );
};
