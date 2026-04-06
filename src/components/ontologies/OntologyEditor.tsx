import React, { useState, useEffect } from "react";
import {
  Box,
  VStack,
  HStack,
  Heading,
  Button,
  Text,
  Tabs,
} from "@chakra-ui/react";
import {
  Save,
  ArrowLeft,
  CheckCircle2,
  AlertTriangle,
  Download,
} from "lucide-react";
import {
  useOntologies,
  Ontology,
  OWLClass,
  OWLObjectProperty,
  OWLDatatypeProperty,
  OntologyMetadata,
} from "@trustgraph/react-state";
import { ClassTree } from "./ClassTree";
import { ClassEditor } from "./ClassEditor";
import { PropertyTree } from "./PropertyTree";
import { PropertyEditor } from "./PropertyEditor";
import { WelcomePanel } from "./WelcomePanel";
import { OntologyValidator, ValidationResult } from "./OntologyValidator";
import { ValidationPanel } from "./ValidationPanel";
import { ExportDialog } from "./ExportDialog";
import { MetadataEditor } from "./MetadataEditor";
import { ConfirmDialog } from "../common/ConfirmDialog";

interface OntologyEditorProps {
  ontologyId: string;
  onBack?: () => void;
}

export const OntologyEditor: React.FC<OntologyEditorProps> = ({
  ontologyId,
  onBack,
}) => {
  const { ontologies, updateOntology } = useOntologies();
  const [selectedClassId, setSelectedClassId] = useState<string | null>(null);
  const [selectedPropertyId, setSelectedPropertyId] = useState<string | null>(
    null,
  );
  const [selectedPropertyType, setSelectedPropertyType] = useState<
    "object" | "datatype" | null
  >(null);
  const [activeTab, setActiveTab] = useState<
    "classes" | "properties" | "metadata"
  >("classes");
  const [showWelcome, setShowWelcome] = useState(false);
  const [validationResult, setValidationResult] =
    useState<ValidationResult | null>(null);
  const [showValidation, setShowValidation] = useState(false);
  const [showExportDialog, setShowExportDialog] = useState(false);
  const [confirmDialog, setConfirmDialog] = useState<{
    isOpen: boolean;
    title: string;
    message: string;
    onConfirm: () => void;
    variant?: "danger" | "warning" | "info";
    confirmText?: string;
  }>({
    isOpen: false,
    title: "",
    message: "",
    onConfirm: () => {},
  });

  // Find the ontology data
  const ontologyData = ontologies.find((ont) => ont[0] === ontologyId)?.[1];

  useEffect(() => {
    if (ontologyData) {
      // Show welcome panel for empty ontologies
      const hasClasses = Object.keys(ontologyData.classes).length > 0;
      const hasProperties =
        Object.keys(ontologyData.objectProperties).length > 0 ||
        Object.keys(ontologyData.datatypeProperties).length > 0;

      setShowWelcome(!hasClasses && !hasProperties);

      // Auto-validate when ontology changes (but don't show validation panel automatically)
      const result = OntologyValidator.validate(ontologyData);
      setValidationResult(result);
    }
  }, [ontologyData]);

  if (!ontologyData) {
    return (
      <Box p={6}>
        <Text color="red.500">Ontology not found: {ontologyId}</Text>
      </Box>
    );
  }

  const handleSave = () => {
    updateOntology({
      id: ontologyId,
      ontology: ontologyData,
    });
  };

  const handleValidate = () => {
    if (!ontologyData) return;

    const result = OntologyValidator.validate(ontologyData);
    setValidationResult(result);
    setShowValidation(true);
  };

  const handleNavigateToItem = (
    itemId: string,
    itemType: "class" | "objectProperty" | "datatypeProperty",
  ) => {
    if (itemType === "class") {
      setSelectedClassId(itemId);
      setSelectedPropertyId(null);
      setSelectedPropertyType(null);
      setActiveTab("classes");
    } else {
      setSelectedPropertyId(itemId);
      setSelectedPropertyType(
        itemType === "objectProperty" ? "object" : "datatype",
      );
      setSelectedClassId(null);
      setActiveTab("properties");
    }
    setShowValidation(false);
  };

  const handleCreateClass = (className: string) => {
    if (!ontologyData) return;

    const classId = className.toLowerCase().replace(/\s+/g, "");
    const classUri = `${ontologyData.metadata.namespace}${classId}`;

    const newClass: OWLClass = {
      uri: classUri,
      type: "owl:Class",
      "rdfs:label": [{ value: className, lang: "en" }],
      "rdfs:comment": "",
    };

    const updatedOntology: Ontology = {
      ...ontologyData,
      classes: {
        ...ontologyData.classes,
        [classId]: newClass,
      },
      metadata: {
        ...ontologyData.metadata,
        modified: new Date().toISOString(),
      },
    };

    updateOntology({
      id: ontologyId,
      ontology: updatedOntology,
    });

    setSelectedClassId(classId);
    setShowWelcome(false);
  };

  const handleUpdateClass = (classId: string, updatedClass: OWLClass) => {
    if (!ontologyData) return;

    const updatedOntology: Ontology = {
      ...ontologyData,
      classes: {
        ...ontologyData.classes,
        [classId]: updatedClass,
      },
      metadata: {
        ...ontologyData.metadata,
        modified: new Date().toISOString(),
      },
    };

    updateOntology({
      id: ontologyId,
      ontology: updatedOntology,
    });
  };

  const handleDeleteClass = (classId: string) => {
    if (!ontologyData) return;

    const classToDelete = ontologyData.classes[classId];
    if (!classToDelete) return;

    // Check for dependencies
    const dependencies = getClassDependencies(classId);

    const className = classToDelete["rdfs:label"]?.[0]?.value || classId;

    if (dependencies.length > 0) {
      const dependencyList = dependencies
        .map((dep) => {
          const depClass = ontologyData.classes[dep];
          return depClass?.["rdfs:label"]?.[0]?.value || dep;
        })
        .join(", ");

      setConfirmDialog({
        isOpen: true,
        title: "Delete Class with Dependencies",
        message: `This class is referenced by other classes: ${dependencyList}.\n\nDeleting "${className}" will remove these relationships and may affect the ontology structure.`,
        onConfirm: () => performDeleteClass(classId),
        variant: "danger",
        confirmText: "Delete Anyway",
      });
    } else {
      setConfirmDialog({
        isOpen: true,
        title: "Delete Class",
        message: `Are you sure you want to delete the class "${className}"?\n\nThis action cannot be undone.`,
        onConfirm: () => performDeleteClass(classId),
        variant: "danger",
        confirmText: "Delete",
      });
    }
  };

  const performDeleteClass = (classId: string) => {
    if (!ontologyData) return;

    // Remove the class and clean up references
    const updatedClasses = { ...ontologyData.classes };
    delete updatedClasses[classId];

    // Remove references to this class from subClassOf relationships
    Object.keys(updatedClasses).forEach((otherClassId) => {
      const otherClass = updatedClasses[otherClassId];
      if (otherClass["rdfs:subClassOf"] === classId) {
        updatedClasses[otherClassId] = {
          ...otherClass,
          "rdfs:subClassOf": undefined,
        };
      }
    });

    // Remove references from properties' domain/range
    const updatedObjectProperties = { ...ontologyData.objectProperties };
    Object.keys(updatedObjectProperties).forEach((propId) => {
      const prop = updatedObjectProperties[propId];

      if (prop["rdfs:domain"] === classId) {
        updatedObjectProperties[propId] = {
          ...prop,
          "rdfs:domain": undefined,
        };
      }
      if (prop["rdfs:range"] === classId) {
        updatedObjectProperties[propId] = {
          ...prop,
          "rdfs:range": undefined,
        };
      }
    });

    const updatedDatatypeProperties = { ...ontologyData.datatypeProperties };
    Object.keys(updatedDatatypeProperties).forEach((propId) => {
      const prop = updatedDatatypeProperties[propId];
      if (prop["rdfs:domain"] === classId) {
        updatedDatatypeProperties[propId] = {
          ...prop,
          "rdfs:domain": undefined,
        };
      }
    });

    const updatedOntology: Ontology = {
      ...ontologyData,
      classes: updatedClasses,
      objectProperties: updatedObjectProperties,
      datatypeProperties: updatedDatatypeProperties,
      metadata: {
        ...ontologyData.metadata,
        modified: new Date().toISOString(),
      },
    };

    updateOntology({
      id: ontologyId,
      ontology: updatedOntology,
    });

    // Clear selection if the deleted class was selected
    if (selectedClassId === classId) {
      setSelectedClassId(null);
    }
  };

  const getClassDependencies = (classId: string): string[] => {
    if (!ontologyData) return [];

    const dependencies: string[] = [];

    // Check subclass relationships
    Object.entries(ontologyData.classes).forEach(
      ([otherClassId, otherClass]) => {
        if (otherClass["rdfs:subClassOf"] === classId) {
          dependencies.push(otherClassId);
        }
      },
    );

    return dependencies;
  };

  const handleDeleteProperty = (
    propertyId: string,
    type: "object" | "datatype",
  ) => {
    if (!ontologyData) return;

    const propertyToDelete =
      type === "object"
        ? ontologyData.objectProperties[propertyId]
        : ontologyData.datatypeProperties[propertyId];

    if (!propertyToDelete) return;

    const propertyName =
      propertyToDelete["rdfs:label"]?.[0]?.value || propertyId;
    const propertyTypeName =
      type === "object" ? "object property" : "datatype property";

    setConfirmDialog({
      isOpen: true,
      title: `Delete ${propertyTypeName}`,
      message: `Are you sure you want to delete the ${propertyTypeName} "${propertyName}"?\n\nThis action cannot be undone.`,
      onConfirm: () => performDeleteProperty(propertyId, type),
      variant: "danger",
      confirmText: "Delete",
    });
  };

  const performDeleteProperty = (
    propertyId: string,
    type: "object" | "datatype",
  ) => {
    if (!ontologyData) return;

    // Remove the property
    const updatedOntology: Ontology = {
      ...ontologyData,
      ...(type === "object"
        ? {
            objectProperties: {
              ...ontologyData.objectProperties,
            },
          }
        : {
            datatypeProperties: {
              ...ontologyData.datatypeProperties,
            },
          }),
      metadata: {
        ...ontologyData.metadata,
        modified: new Date().toISOString(),
      },
    };

    // Remove the property from the appropriate collection
    if (type === "object") {
      delete updatedOntology.objectProperties[propertyId];
    } else {
      delete updatedOntology.datatypeProperties[propertyId];
    }

    updateOntology({
      id: ontologyId,
      ontology: updatedOntology,
    });

    // Clear selection if the deleted property was selected
    if (selectedPropertyId === propertyId && selectedPropertyType === type) {
      setSelectedPropertyId(null);
      setSelectedPropertyType(null);
    }
  };

  const handleCreateObjectProperty = (propertyName: string) => {
    if (!ontologyData) return;

    const propertyId = propertyName.toLowerCase().replace(/\s+/g, "");
    const propertyUri = `${ontologyData.metadata.namespace}${propertyId}`;

    const newProperty: OWLObjectProperty = {
      uri: propertyUri,
      type: "owl:ObjectProperty",
      "rdfs:label": [{ value: propertyName, lang: "en" }],
      "rdfs:comment": "",
    };

    const updatedOntology: Ontology = {
      ...ontologyData,
      objectProperties: {
        ...ontologyData.objectProperties,
        [propertyId]: newProperty,
      },
      metadata: {
        ...ontologyData.metadata,
        modified: new Date().toISOString(),
      },
    };

    updateOntology({
      id: ontologyId,
      ontology: updatedOntology,
    });

    setSelectedPropertyId(propertyId);
    setSelectedPropertyType("object");
    setActiveTab("properties");
    setShowWelcome(false);
  };

  const handleCreateDatatypeProperty = (propertyName: string) => {
    if (!ontologyData) return;

    const propertyId = propertyName.toLowerCase().replace(/\s+/g, "");
    const propertyUri = `${ontologyData.metadata.namespace}${propertyId}`;

    const newProperty: OWLDatatypeProperty = {
      uri: propertyUri,
      type: "owl:DatatypeProperty",
      "rdfs:label": [{ value: propertyName, lang: "en" }],
      "rdfs:comment": "",
      "rdfs:range": "xsd:string",
    };

    const updatedOntology: Ontology = {
      ...ontologyData,
      datatypeProperties: {
        ...ontologyData.datatypeProperties,
        [propertyId]: newProperty,
      },
      metadata: {
        ...ontologyData.metadata,
        modified: new Date().toISOString(),
      },
    };

    updateOntology({
      id: ontologyId,
      ontology: updatedOntology,
    });

    setSelectedPropertyId(propertyId);
    setSelectedPropertyType("datatype");
    setActiveTab("properties");
    setShowWelcome(false);
  };

  const handleSelectProperty = (
    propertyId: string,
    type: "object" | "datatype",
  ) => {
    setSelectedPropertyId(propertyId);
    setSelectedPropertyType(type);
    setSelectedClassId(null); // Clear class selection
  };

  const handleSelectClass = (classId: string) => {
    setSelectedClassId(classId);
    setSelectedPropertyId(null); // Clear property selection
    setSelectedPropertyType(null);
    setActiveTab("classes");
  };

  const handleUpdateProperty = (
    propertyId: string,
    updatedProperty: OWLObjectProperty | OWLDatatypeProperty,
    type: "object" | "datatype",
  ) => {
    if (!ontologyData) return;

    const updatedOntology: Ontology = {
      ...ontologyData,
      ...(type === "object"
        ? {
            objectProperties: {
              ...ontologyData.objectProperties,
              [propertyId]: updatedProperty as OWLObjectProperty,
            },
          }
        : {
            datatypeProperties: {
              ...ontologyData.datatypeProperties,
              [propertyId]: updatedProperty as OWLDatatypeProperty,
            },
          }),
      metadata: {
        ...ontologyData.metadata,
        modified: new Date().toISOString(),
      },
    };

    updateOntology({
      id: ontologyId,
      ontology: updatedOntology,
    });
  };

  const handleUpdateMetadata = (metadata: OntologyMetadata) => {
    if (!ontologyData) return;

    const updatedOntology: Ontology = {
      ...ontologyData,
      metadata,
    };

    updateOntology({
      id: ontologyId,
      ontology: updatedOntology,
    });
  };

  const selectedClass = selectedClassId
    ? ontologyData.classes[selectedClassId]
    : null;
  const selectedProperty =
    selectedPropertyId && selectedPropertyType
      ? selectedPropertyType === "object"
        ? ontologyData.objectProperties[selectedPropertyId]
        : ontologyData.datatypeProperties[selectedPropertyId]
      : null;

  return (
    <Box
      h="calc(100vh - 140px)"
      display="flex"
      flexDirection="column"
      bg="gray.25"
    >
      {/* Header */}
      <Box p={6} borderBottomWidth="1px" bg="white" boxShadow="sm">
        <HStack justify="space-between" align="center">
          <HStack>
            {onBack && (
              <Button variant="ghost" size="sm" onClick={onBack}>
                <ArrowLeft size={16} />
              </Button>
            )}
            <VStack align="start" spacing={0}>
              <Heading size="lg">{ontologyData.metadata.name}</Heading>
              <Text fontSize="sm" color="gray.600">
                {ontologyData.metadata.description}
              </Text>
            </VStack>
          </HStack>
          <HStack>
            <Button
              variant="outline"
              onClick={handleValidate}
              colorPalette={
                validationResult?.isValid === false
                  ? "red"
                  : validationResult?.isValid === true
                    ? "green"
                    : "gray"
              }
            >
              {validationResult?.isValid === false ? (
                <AlertTriangle size={16} style={{ marginRight: "8px" }} />
              ) : validationResult?.isValid === true ? (
                <CheckCircle2 size={16} style={{ marginRight: "8px" }} />
              ) : null}
              Validate
            </Button>
            <Button
              variant="outline"
              onClick={() => setShowExportDialog(true)}
            >
              <Download size={16} style={{ marginRight: "8px" }} />
              Export
            </Button>
            <Button colorPalette="primary" onClick={handleSave}>
              <Save size={16} style={{ marginRight: "8px" }} />
              Save
            </Button>
          </HStack>
        </HStack>
      </Box>

      {/* Validation Panel */}
      {showValidation && validationResult && (
        <Box p={6} borderBottomWidth="1px" bg="white" boxShadow="sm">
          <ValidationPanel
            validationResult={validationResult}
            onNavigateToItem={handleNavigateToItem}
            onClose={() => setShowValidation(false)}
          />
        </Box>
      )}

      {/* Main Content */}
      <Box flex="1" display="flex" minH="0">
        {showWelcome ? (
          <Box
            flex="1"
            p={6}
            display="flex"
            alignItems="center"
            justifyContent="center"
          >
            <WelcomePanel
              ontologyName={ontologyData.metadata.name}
              onCreateClass={handleCreateClass}
              onDismiss={() => setShowWelcome(false)}
            />
          </Box>
        ) : (
          <>
            {/* Left Panel - Tabbed Navigation */}
            <Box
              w="380px"
              borderRightWidth="1px"
              bg="white"
              overflow="auto"
              boxShadow="sm"
            >
              <Tabs.Root
                value={activeTab}
                onValueChange={(details) =>
                  setActiveTab(
                    details.value as "classes" | "properties" | "metadata",
                  )
                }
              >
                <Tabs.List>
                  <Tabs.Trigger value="classes">Classes</Tabs.Trigger>
                  <Tabs.Trigger value="properties">Properties</Tabs.Trigger>
                  <Tabs.Trigger value="metadata">Metadata</Tabs.Trigger>
                </Tabs.List>

                <Tabs.Content value="classes">
                  <ClassTree
                    classes={ontologyData.classes}
                    selectedClassId={selectedClassId}
                    onSelectClass={handleSelectClass}
                    onCreateClass={handleCreateClass}
                    onUpdateClass={handleUpdateClass}
                    onDeleteClass={handleDeleteClass}
                  />
                </Tabs.Content>

                <Tabs.Content value="properties">
                  <PropertyTree
                    objectProperties={ontologyData.objectProperties}
                    datatypeProperties={ontologyData.datatypeProperties}
                    selectedPropertyId={selectedPropertyId}
                    selectedPropertyType={selectedPropertyType}
                    onSelectProperty={handleSelectProperty}
                    onCreateObjectProperty={handleCreateObjectProperty}
                    onCreateDatatypeProperty={handleCreateDatatypeProperty}
                    onDeleteProperty={handleDeleteProperty}
                  />
                </Tabs.Content>

                <Tabs.Content value="metadata">
                  <Box p={6}>
                    <VStack spacing={4}>
                      <Text
                        fontSize="lg"
                        fontWeight="semibold"
                        color="gray.700"
                      >
                        Ontology Information
                      </Text>
                      <Text fontSize="sm" color="gray.600">
                        Configure basic metadata about this ontology
                      </Text>
                    </VStack>
                  </Box>
                </Tabs.Content>
              </Tabs.Root>
            </Box>

            {/* Right Panel - Editor */}
            <Box flex="1" overflow="auto" bg="white">
              {activeTab === "metadata" ? (
                <MetadataEditor
                  metadata={ontologyData.metadata}
                  onUpdateMetadata={handleUpdateMetadata}
                  hasClasses={Object.keys(ontologyData.classes).length > 0}
                  hasProperties={
                    Object.keys(ontologyData.objectProperties).length > 0 ||
                    Object.keys(ontologyData.datatypeProperties).length > 0
                  }
                />
              ) : selectedClass && selectedClassId ? (
                <ClassEditor
                  classId={selectedClassId}
                  owlClass={selectedClass}
                  ontology={ontologyData}
                  onUpdateClass={handleUpdateClass}
                  onDeleteClass={handleDeleteClass}
                  onNavigateToProperty={(propertyId, propertyType) => {
                    setSelectedPropertyId(propertyId);
                    setSelectedPropertyType(
                      propertyType === "objectProperty"
                        ? "object"
                        : "datatype",
                    );
                    setSelectedClassId(null);
                    setActiveTab("properties");
                  }}
                />
              ) : selectedProperty &&
                selectedPropertyId &&
                selectedPropertyType ? (
                <PropertyEditor
                  propertyId={selectedPropertyId}
                  property={selectedProperty}
                  propertyType={selectedPropertyType}
                  ontology={ontologyData}
                  onUpdateProperty={handleUpdateProperty}
                  onDeleteProperty={handleDeleteProperty}
                />
              ) : (
                <Box
                  p={6}
                  display="flex"
                  alignItems="center"
                  justifyContent="center"
                  h="100%"
                >
                  <VStack spacing={4}>
                    <Text color="gray.500" fontSize="lg">
                      {activeTab === "classes"
                        ? "Select a class to edit"
                        : activeTab === "properties"
                          ? "Select a property to edit"
                          : "Select an item to edit"}
                    </Text>
                    <Text color="gray.400" fontSize="sm" textAlign="center">
                      {activeTab === "classes"
                        ? "Choose a class from the navigation panel or create a new one to get started"
                        : activeTab === "properties"
                          ? "Choose a property from the navigation panel or create a new one to get started"
                          : "Choose an item from the navigation panel or create new content to get started"}
                    </Text>
                  </VStack>
                </Box>
              )}
            </Box>
          </>
        )}
      </Box>

      {/* Export Dialog */}
      <ExportDialog
        ontology={ontologyData}
        isOpen={showExportDialog}
        onClose={() => setShowExportDialog(false)}
      />

      {/* Confirm Dialog */}
      <ConfirmDialog
        isOpen={confirmDialog.isOpen}
        onClose={() => setConfirmDialog({ ...confirmDialog, isOpen: false })}
        onConfirm={confirmDialog.onConfirm}
        title={confirmDialog.title}
        message={confirmDialog.message}
        variant={confirmDialog.variant}
        confirmText={confirmDialog.confirmText}
      />
    </Box>
  );
};
