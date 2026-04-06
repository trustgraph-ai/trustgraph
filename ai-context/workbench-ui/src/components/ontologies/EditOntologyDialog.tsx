import React, { useState, useEffect } from "react";
import { Portal, Button, Dialog, CloseButton, Tabs } from "@chakra-ui/react";
import { useNotification } from "@trustgraph/react-state";
import {
  useOntologies,
  Ontology,
  OntologyConcept,
} from "@trustgraph/react-state";
import { validateOntology } from "../../utils/skos-validation";
import { OntologyMetadataTab } from "./OntologyMetadataTab";
import { OntologyConceptsTab } from "./OntologyConceptsTab";
import { OntologySchemeTab } from "./OntologySchemeTab";
import { OntologyJsonPreviewTab } from "./OntologyJsonPreviewTab";
import { OntologyValidationTab } from "./OntologyValidationTab";

interface EditOntologyDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: "create" | "edit";
  ontologyId?: string;
  initialOntology?: Ontology;
}

export const EditOntologyDialog: React.FC<EditOntologyDialogProps> = ({
  open,
  onOpenChange,
  mode,
  ontologyId: initialOntologyId,
  initialOntology,
}) => {
  const {
    createOntology,
    updateOntology,
    deleteOntology,
    isCreatingOntology,
    isUpdatingOntology,
    isDeletingOntology,
  } = useOntologies();
  const notify = useNotification();

  const [ontologyId, setOntologyId] = useState(initialOntologyId || "");
  const [ontology, setOntology] = useState<Ontology>(
    initialOntology || {
      metadata: {
        name: "",
        description: "",
        version: "1.0",
        created: new Date().toISOString(),
        modified: new Date().toISOString(),
        creator: "user",
        namespace: "http://example.org/ontologies/",
      },
      concepts: {},
      scheme: {
        uri: "",
        prefLabel: "",
        hasTopConcept: [],
      },
    },
  );

  useEffect(() => {
    if (initialOntology) {
      setOntology(initialOntology);
    }
    if (initialOntologyId) {
      setOntologyId(initialOntologyId);
    }
  }, [initialOntology, initialOntologyId]);

  const handleSave = () => {
    if (!ontologyId.trim()) {
      notify.error("Ontology ID is required");
      return;
    }

    if (!ontology.metadata.name.trim()) {
      notify.error("Ontology name is required");
      return;
    }

    const updatedOntology = {
      ...ontology,
      metadata: {
        ...ontology.metadata,
        modified: new Date().toISOString(),
      },
      scheme: {
        ...ontology.scheme,
        uri:
          ontology.scheme.uri || `${ontology.metadata.namespace}${ontologyId}`,
        prefLabel: ontology.scheme.prefLabel || ontology.metadata.name,
      },
    };

    // Run validation and warn about issues
    const validation = validateOntology(updatedOntology);

    if (validation.errors.length > 0) {
      const shouldContinue = window.confirm(
        `This ontology has ${validation.errors.length} validation error${validation.errors.length !== 1 ? "s" : ""}. ` +
          "Saving may result in an invalid SKOS ontology. Do you want to continue?",
      );
      if (!shouldContinue) return;
    } else if (validation.warnings.length > 0) {
      notify.warning(
        `Ontology saved with ${validation.warnings.length} validation warning${validation.warnings.length !== 1 ? "s" : ""}`,
      );
    }

    const mutation = mode === "create" ? createOntology : updateOntology;
    mutation({
      id: ontologyId,
      ontology: updatedOntology,
      onSuccess: () => {
        onOpenChange(false);
      },
    });
  };

  const handleDelete = () => {
    if (
      window.confirm(
        `Are you sure you want to delete the ontology "${ontology.metadata.name}"?`,
      )
    ) {
      deleteOntology({
        id: ontologyId,
        onSuccess: () => {
          onOpenChange(false);
        },
      });
    }
  };

  const handleMetadataChange = (field: string, value: string) => {
    setOntology({
      ...ontology,
      metadata: {
        ...ontology.metadata,
        [field]: value,
      },
    });
  };

  const handleSchemeChange = (field: string, value: string) => {
    setOntology({
      ...ontology,
      scheme: {
        ...ontology.scheme,
        [field]: value,
      },
    });
  };

  const addConcept = () => {
    const newId = `concept-${Date.now()}`;
    const newConcept: OntologyConcept = {
      id: newId,
      prefLabel: "New Concept",
      narrower: [],
      related: [],
    };

    setOntology({
      ...ontology,
      concepts: {
        ...ontology.concepts,
        [newId]: newConcept,
      },
    });
  };

  const updateConcept = (conceptId: string, field: string, value: unknown) => {
    setOntology({
      ...ontology,
      concepts: {
        ...ontology.concepts,
        [conceptId]: {
          ...ontology.concepts[conceptId],
          [field]: value,
        },
      },
    });
  };

  const deleteConcept = (conceptId: string) => {
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { [conceptId]: _, ...remainingConcepts } = ontology.concepts;
    setOntology({
      ...ontology,
      concepts: remainingConcepts,
    });
  };

  const isLoading =
    isCreatingOntology || isUpdatingOntology || isDeletingOntology;

  return (
    <Dialog.Root
      placement="center"
      size="xl"
      open={open}
      onOpenChange={(x) => {
        onOpenChange(x.open);
      }}
    >
      <Portal>
        <Dialog.Backdrop />
        <Dialog.Positioner>
          <Dialog.Content maxW="4xl">
            <Dialog.Header>
              <Dialog.Title>
                {mode === "create" ? "Create New Ontology" : "Edit Ontology"}
              </Dialog.Title>
            </Dialog.Header>
            <Dialog.Body>
              <Tabs.Root defaultValue="metadata">
                <Tabs.List>
                  <Tabs.Trigger value="metadata">Metadata</Tabs.Trigger>
                  <Tabs.Trigger value="concepts">
                    Concepts ({Object.keys(ontology.concepts).length})
                  </Tabs.Trigger>
                  <Tabs.Trigger value="scheme">Scheme</Tabs.Trigger>
                  <Tabs.Trigger value="validation">Validation</Tabs.Trigger>
                  <Tabs.Trigger value="json">JSON Preview</Tabs.Trigger>
                </Tabs.List>

                <Tabs.Content value="metadata">
                  <OntologyMetadataTab
                    ontologyId={ontologyId}
                    ontology={ontology}
                    mode={mode}
                    onOntologyIdChange={setOntologyId}
                    onMetadataChange={handleMetadataChange}
                  />
                </Tabs.Content>

                <Tabs.Content value="concepts">
                  <OntologyConceptsTab
                    ontology={ontology}
                    onAddConcept={addConcept}
                    onDeleteConcept={deleteConcept}
                    onUpdateConcept={updateConcept}
                  />
                </Tabs.Content>

                <Tabs.Content value="scheme">
                  <OntologySchemeTab
                    ontology={ontology}
                    onSchemeChange={handleSchemeChange}
                  />
                </Tabs.Content>

                <Tabs.Content value="validation">
                  <OntologyValidationTab
                    ontology={ontology}
                    onOntologyChange={setOntology}
                  />
                </Tabs.Content>

                <Tabs.Content value="json">
                  <OntologyJsonPreviewTab ontology={ontology} />
                </Tabs.Content>
              </Tabs.Root>
            </Dialog.Body>

            <Dialog.Footer>
              <Button
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isLoading}
              >
                Cancel
              </Button>
              {mode === "edit" && (
                <Button
                  colorPalette="red"
                  variant="solid"
                  onClick={handleDelete}
                  loading={isDeletingOntology}
                >
                  Delete
                </Button>
              )}
              <Button
                colorPalette="primary"
                onClick={handleSave}
                loading={isLoading}
              >
                {mode === "create" ? "Create" : "Save"}
              </Button>
            </Dialog.Footer>

            <Dialog.CloseTrigger asChild>
              <CloseButton size="sm" />
            </Dialog.CloseTrigger>
          </Dialog.Content>
        </Dialog.Positioner>
      </Portal>
    </Dialog.Root>
  );
};
