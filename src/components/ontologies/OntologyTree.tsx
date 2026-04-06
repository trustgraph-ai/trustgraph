import React, { useState, useMemo } from "react";
import { Box, VStack } from "@chakra-ui/react";
import { Ontology } from "@trustgraph/react-state";
import { OntologyTreeNode } from "./OntologyTreeNode";
import { OntologyTreeSearch } from "./OntologyTreeSearch";
import { OntologyTreeHeader } from "./OntologyTreeHeader";
import { OntologyTreeEmpty } from "./OntologyTreeEmpty";

interface OntologyTreeProps {
  ontology: Ontology;
  selectedConceptId?: string;
  onConceptSelect: (conceptId: string) => void;
  onConceptAdd: (parentId?: string) => void;
  onConceptEdit: (conceptId: string) => void;
  onConceptDelete: (conceptId: string) => void;
  onConceptMove: (conceptId: string, newParentId?: string) => void;
}

export const OntologyTree: React.FC<OntologyTreeProps> = ({
  ontology,
  selectedConceptId,
  onConceptSelect,
  onConceptAdd,
  onConceptEdit,
  onConceptDelete,
  onConceptMove,
}) => {
  const [searchTerm, setSearchTerm] = useState("");

  // Get top-level concepts (those marked as topConcept or in hasTopConcept)
  const topConcepts = useMemo(() => {
    const topConceptIds = ontology.scheme?.hasTopConcept || [];
    const conceptsWithTopFlag = Object.values(ontology.concepts)
      .filter((c) => c.topConcept)
      .map((c) => c.id);

    // Combine both sources and remove duplicates
    const allTopIds = [...new Set([...topConceptIds, ...conceptsWithTopFlag])];

    return allTopIds.map((id) => ontology.concepts[id]).filter(Boolean);
  }, [ontology.concepts, ontology.scheme?.hasTopConcept]);

  // Get orphaned concepts (no broader relation and not in top concepts)
  const orphanedConcepts = useMemo(() => {
    const topConceptIds = new Set(topConcepts.map((c) => c.id));
    return Object.values(ontology.concepts)
      .filter((concept) => !concept.broader && !topConceptIds.has(concept.id))
      .filter((concept) => !concept.topConcept);
  }, [ontology.concepts, topConcepts]);

  const allRootConcepts = [...topConcepts, ...orphanedConcepts];

  if (Object.keys(ontology.concepts).length === 0) {
    return <OntologyTreeEmpty onAddConcept={() => onConceptAdd()} />;
  }

  return (
    <VStack gap={4} align="stretch" h="100%">
      <OntologyTreeSearch
        searchTerm={searchTerm}
        onSearchChange={setSearchTerm}
      />

      <OntologyTreeHeader
        conceptCount={Object.keys(ontology.concepts).length}
        onAddRootConcept={() => onConceptAdd()}
      />

      {/* Tree */}
      <Box flex="1" overflowY="auto">
        <VStack gap={1} align="stretch">
          {allRootConcepts.map((concept) => (
            <OntologyTreeNode
              key={concept.id}
              concept={concept}
              ontology={ontology}
              level={0}
              isSelected={selectedConceptId === concept.id}
              searchTerm={searchTerm}
              selectedConceptId={selectedConceptId}
              onSelect={onConceptSelect}
              onAdd={onConceptAdd}
              onEdit={onConceptEdit}
              onDelete={onConceptDelete}
              onMove={onConceptMove}
            />
          ))}
        </VStack>
      </Box>
    </VStack>
  );
};
