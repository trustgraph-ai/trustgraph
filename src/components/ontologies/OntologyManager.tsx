import React, { useState } from "react";
import { Box, Grid, GridItem, VStack } from "@chakra-ui/react";
import { OntologyManagerHeader } from "./OntologyManagerHeader";
import { ConceptDetailView } from "./ConceptDetailView";
import { OntologyEmptyStates } from "./OntologyEmptyStates";
import { SKOSDialog } from "./SKOSDialog";
import { useNotification } from "@trustgraph/react-state";
import {
  useOntologies,
  Ontology,
  OntologyConcept,
} from "@trustgraph/react-state";
import { OntologyTree } from "./OntologyTree";
import { ConceptEditor } from "./ConceptEditor";

interface OntologyManagerProps {
  selectedOntologyId?: string;
  onOntologySelect?: (ontologyId: string) => void;
}

export const OntologyManager: React.FC<OntologyManagerProps> = ({
  selectedOntologyId,
  onOntologySelect,
}) => {
  const { ontologies, updateOntology, createOntology } = useOntologies();
  const notify = useNotification();

  const [currentOntologyId, setCurrentOntologyId] = useState<string | null>(
    selectedOntologyId || null,
  );
  const [selectedConceptId, setSelectedConceptId] = useState<string | null>(
    null,
  );
  const [editingConcept, setEditingConcept] = useState<OntologyConcept | null>(
    null,
  );
  const [isCreatingConcept, setIsCreatingConcept] = useState(false);
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [importDialogOpen, setImportDialogOpen] = useState(false);

  const currentOntology = currentOntologyId
    ? ontologies.find(([id]) => id === currentOntologyId)?.[1]
    : null;

  const selectedConcept =
    selectedConceptId && currentOntology
      ? currentOntology.concepts[selectedConceptId]
      : null;

  const handleOntologyChange = (ontologyId: string) => {
    setCurrentOntologyId(ontologyId);
    setSelectedConceptId(null);
    setEditingConcept(null);
    setIsCreatingConcept(false);
    onOntologySelect?.(ontologyId);
  };

  const handleConceptSelect = (conceptId: string) => {
    setSelectedConceptId(conceptId);
    setEditingConcept(null);
    setIsCreatingConcept(false);
  };

  const handleConceptAdd = (parentId?: string) => {
    if (!currentOntology || !currentOntologyId) return;

    const newConcept: OntologyConcept = {
      id: `concept-${Date.now()}`,
      prefLabel: "New Concept",
      broader: parentId || null,
      narrower: [],
      related: [],
      topConcept: !parentId, // If no parent, make it a top concept
    };

    setEditingConcept(newConcept);
    setIsCreatingConcept(true);
    setSelectedConceptId(newConcept.id);
  };

  const handleConceptEdit = (conceptId: string) => {
    if (!currentOntology) return;
    const concept = currentOntology.concepts[conceptId];
    if (concept) {
      setEditingConcept({ ...concept });
      setIsCreatingConcept(false);
      setSelectedConceptId(conceptId);
    }
  };

  const handleConceptSave = (concept: OntologyConcept) => {
    if (!currentOntology || !currentOntologyId) return;

    // Update the ontology with the new/modified concept
    const updatedConcepts = {
      ...currentOntology.concepts,
      [concept.id]: concept,
    };

    // Update broader/narrower relationships
    if (concept.broader) {
      const parent = updatedConcepts[concept.broader];
      if (parent && !parent.narrower?.includes(concept.id)) {
        parent.narrower = [...(parent.narrower || []), concept.id];
      }
    }

    // Update scheme's hasTopConcept if this is a top concept
    const updatedScheme = { ...currentOntology.scheme };
    if (
      concept.topConcept &&
      !updatedScheme.hasTopConcept.includes(concept.id)
    ) {
      updatedScheme.hasTopConcept = [
        ...updatedScheme.hasTopConcept,
        concept.id,
      ];
    } else if (
      !concept.topConcept &&
      updatedScheme.hasTopConcept.includes(concept.id)
    ) {
      updatedScheme.hasTopConcept = updatedScheme.hasTopConcept.filter(
        (id) => id !== concept.id,
      );
    }

    const updatedOntology: Ontology = {
      ...currentOntology,
      concepts: updatedConcepts,
      scheme: updatedScheme,
      metadata: {
        ...currentOntology.metadata,
        modified: new Date().toISOString(),
      },
    };

    updateOntology({
      id: currentOntologyId,
      ontology: updatedOntology,
      onSuccess: () => {
        setEditingConcept(null);
        setIsCreatingConcept(false);
        setSelectedConceptId(concept.id);
        notify.success(
          isCreatingConcept ? "Concept created" : "Concept updated",
        );
      },
    });
  };

  const handleConceptDelete = (conceptId: string) => {
    if (!currentOntology || !currentOntologyId) return;

    if (
      window.confirm(
        "Are you sure you want to delete this concept? This action cannot be undone.",
      )
    ) {
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      const { [conceptId]: deleted, ...remainingConcepts } =
        currentOntology.concepts;

      // Remove from parent's narrower list
      Object.values(remainingConcepts).forEach((concept) => {
        if (concept.narrower?.includes(conceptId)) {
          concept.narrower = concept.narrower.filter((id) => id !== conceptId);
        }
        if (concept.related?.includes(conceptId)) {
          concept.related = concept.related.filter((id) => id !== conceptId);
        }
      });

      // Remove from scheme's hasTopConcept
      const updatedScheme = {
        ...currentOntology.scheme,
        hasTopConcept: currentOntology.scheme.hasTopConcept.filter(
          (id) => id !== conceptId,
        ),
      };

      const updatedOntology: Ontology = {
        ...currentOntology,
        concepts: remainingConcepts,
        scheme: updatedScheme,
        metadata: {
          ...currentOntology.metadata,
          modified: new Date().toISOString(),
        },
      };

      updateOntology({
        id: currentOntologyId,
        ontology: updatedOntology,
        onSuccess: () => {
          setSelectedConceptId(null);
          setEditingConcept(null);
          notify.success("Concept deleted");
        },
      });
    }
  };

  const handleConceptMove = () => {
    // TODO: Implement drag-and-drop concept moving
    notify.info(
      "Drag-and-drop concept moving will be implemented in a future update",
    );
  };

  const getConceptBreadcrumb = (conceptId: string): string[] => {
    if (!currentOntology || !conceptId) return [];

    const path: string[] = [];
    let currentId: string | null = conceptId;

    while (currentId) {
      const concept = currentOntology.concepts[currentId];
      if (!concept) break;

      path.unshift(concept.prefLabel);
      currentId = concept.broader;
    }

    return path;
  };

  const handleImportOntology = (
    importedOntology: Ontology,
    ontologyId: string,
  ) => {
    createOntology({
      id: ontologyId,
      ontology: importedOntology,
      onSuccess: () => {
        setCurrentOntologyId(ontologyId);
        setSelectedConceptId(null);
        setEditingConcept(null);
        setIsCreatingConcept(false);
        notify.success(
          `Ontology "${importedOntology.metadata.name}" imported successfully`,
        );
      },
    });
  };

  const handleExportOntology = () => {
    if (!currentOntology) {
      notify.error("No ontology selected for export");
      return;
    }
    setExportDialogOpen(true);
  };

  const handleImportDialogOpen = () => {
    setImportDialogOpen(true);
  };

  if (!ontologies.length) {
    return <OntologyEmptyStates type="no-ontologies" />;
  }

  if (!currentOntology) {
    return (
      <OntologyEmptyStates
        type="no-ontology-selected"
        ontologies={ontologies}
        onOntologyChange={handleOntologyChange}
      />
    );
  }

  return (
    <VStack gap={4} align="stretch" h="100%">
      {/* Header */}
      <OntologyManagerHeader
        currentOntology={currentOntology}
        currentOntologyId={currentOntologyId}
        selectedConcept={selectedConcept}
        ontologies={ontologies}
        conceptBreadcrumb={
          selectedConcept ? getConceptBreadcrumb(selectedConcept.id) : []
        }
        onOntologyChange={handleOntologyChange}
        onConceptAdd={() => handleConceptAdd()}
        onImport={handleImportDialogOpen}
        onExport={handleExportOntology}
        onSettings={() => notify.info("Settings feature coming soon")}
      />

      {/* Main Content */}
      <Grid templateColumns="1fr 1px 2fr" gap={0} flex="1" minH="0">
        {/* Left Panel - Tree View */}
        <GridItem>
          <Box h="100%" p={4} overflowY="auto">
            <OntologyTree
              ontology={currentOntology}
              selectedConceptId={selectedConceptId}
              onConceptSelect={handleConceptSelect}
              onConceptAdd={handleConceptAdd}
              onConceptEdit={handleConceptEdit}
              onConceptDelete={handleConceptDelete}
              onConceptMove={handleConceptMove}
            />
          </Box>
        </GridItem>

        {/* Divider */}
        <GridItem>
          <Box w="1px" h="100%" bg="bg.subtle" />
        </GridItem>

        {/* Right Panel - Concept Editor */}
        <GridItem>
          <Box h="100%" p={4}>
            {editingConcept ? (
              <ConceptEditor
                concept={editingConcept}
                ontology={currentOntology}
                onSave={handleConceptSave}
                onCancel={() => {
                  setEditingConcept(null);
                  setIsCreatingConcept(false);
                  if (isCreatingConcept) {
                    setSelectedConceptId(null);
                  }
                }}
              />
            ) : selectedConcept ? (
              <ConceptDetailView
                concept={selectedConcept}
                onEdit={() => handleConceptEdit(selectedConcept.id)}
              />
            ) : (
              <OntologyEmptyStates type="no-concept-selected" />
            )}
          </Box>
        </GridItem>
      </Grid>

      {/* SKOS Export Dialog */}
      <SKOSDialog
        open={exportDialogOpen}
        onOpenChange={setExportDialogOpen}
        mode="export"
        ontology={currentOntology || undefined}
      />

      {/* SKOS Import Dialog */}
      <SKOSDialog
        open={importDialogOpen}
        onOpenChange={setImportDialogOpen}
        mode="import"
        onImport={handleImportOntology}
      />
    </VStack>
  );
};
