import React, { useState, useEffect } from "react";
import {
  Box,
  VStack,
  HStack,
  Text,
  Input,
  Textarea,
  Button,
  Field,
  Separator,
  Badge,
} from "@chakra-ui/react";
import SelectField from "../common/SelectField";
import SelectOptionText from "../common/SelectOptionText";
import { Hash, Save, Trash2, Link, Type, AlertTriangle } from "lucide-react";
import { OWLClass, Ontology } from "@trustgraph/react-state";
import { MultiLanguageLabels } from "./MultiLanguageLabels";

interface ClassEditorProps {
  classId: string;
  owlClass: OWLClass;
  ontology: Ontology;
  onUpdateClass: (classId: string, updatedClass: OWLClass) => void;
  onDeleteClass: (classId: string) => void;
  onNavigateToProperty?: (
    propertyId: string,
    propertyType: "objectProperty" | "datatypeProperty",
  ) => void;
}

export const ClassEditor: React.FC<ClassEditorProps> = ({
  classId,
  owlClass,
  ontology,
  onUpdateClass,
  onDeleteClass,
  onNavigateToProperty,
}) => {
  const [labels, setLabels] = useState<
    Array<{ value: string; lang?: string }>
  >([]);
  const [comment, setComment] = useState("");
  const [subClassOf, setSubClassOf] = useState("");
  const [equivalentClasses, setEquivalentClasses] = useState<string[]>([]);
  const [disjointClasses, setDisjointClasses] = useState<string[]>([]);
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    // Initialize form with current values
    const currentLabels = owlClass["rdfs:label"] || [
      { value: "", lang: "en" },
    ];
    const currentComment = owlClass["rdfs:comment"] || "";
    const currentSubClassOf = owlClass["rdfs:subClassOf"] || "";
    const currentEquivalentClasses = owlClass["owl:equivalentClass"] || [];
    const currentDisjointClasses = owlClass["owl:disjointWith"] || [];

    setLabels(currentLabels);
    setComment(currentComment);
    setSubClassOf(currentSubClassOf);
    setEquivalentClasses(currentEquivalentClasses);
    setDisjointClasses(currentDisjointClasses);
    setHasChanges(false);
  }, [classId, owlClass]);

  useEffect(() => {
    // Check for changes
    const currentLabels = owlClass["rdfs:label"] || [
      { value: "", lang: "en" },
    ];
    const currentComment = owlClass["rdfs:comment"] || "";
    const currentSubClassOf = owlClass["rdfs:subClassOf"] || "";
    const currentEquivalentClasses = owlClass["owl:equivalentClass"] || [];
    const currentDisjointClasses = owlClass["owl:disjointWith"] || [];

    const labelsChanged =
      JSON.stringify(labels) !== JSON.stringify(currentLabels);
    const commentChanged = comment !== currentComment;
    const subClassOfChanged = subClassOf !== currentSubClassOf;
    const equivalentClassesChanged =
      JSON.stringify(equivalentClasses) !==
      JSON.stringify(currentEquivalentClasses);
    const disjointClassesChanged =
      JSON.stringify(disjointClasses) !==
      JSON.stringify(currentDisjointClasses);

    setHasChanges(
      labelsChanged ||
        commentChanged ||
        subClassOfChanged ||
        equivalentClassesChanged ||
        disjointClassesChanged,
    );
  }, [
    labels,
    comment,
    subClassOf,
    equivalentClasses,
    disjointClasses,
    owlClass,
  ]);

  const handleSave = () => {
    const validLabels = labels.filter((l) => l.value.trim());
    const validEquivalentClasses = equivalentClasses.filter((c) => c.trim());
    const validDisjointClasses = disjointClasses.filter((c) => c.trim());

    const updatedClass: OWLClass = {
      ...owlClass,
      "rdfs:label": validLabels.length > 0 ? validLabels : [],
      "rdfs:comment": comment.trim(),
      "rdfs:subClassOf": subClassOf.trim() || undefined,
      "owl:equivalentClass":
        validEquivalentClasses.length > 0 ? validEquivalentClasses : undefined,
      "owl:disjointWith":
        validDisjointClasses.length > 0 ? validDisjointClasses : undefined,
    };

    onUpdateClass(classId, updatedClass);
    setHasChanges(false);
  };

  const handleReset = () => {
    const currentLabels = owlClass["rdfs:label"] || [
      { value: "", lang: "en" },
    ];
    const currentComment = owlClass["rdfs:comment"] || "";
    const currentSubClassOf = owlClass["rdfs:subClassOf"] || "";
    const currentEquivalentClasses = owlClass["owl:equivalentClass"] || [];
    const currentDisjointClasses = owlClass["owl:disjointWith"] || [];

    setLabels(currentLabels);
    setComment(currentComment);
    setSubClassOf(currentSubClassOf);
    setEquivalentClasses(currentEquivalentClasses);
    setDisjointClasses(currentDisjointClasses);
    setHasChanges(false);
  };

  return (
    <Box h="100%" display="flex" flexDirection="column">
      {/* Header */}
      <Box p={4} borderBottomWidth="1px">
        <HStack justify="space-between" align="center">
          <HStack>
            <Hash size={20} color="#666" />
            <VStack align="start" spacing={0}>
              <Text fontSize="lg" fontWeight="semibold">
                {labels[0]?.value ||
                  owlClass["rdfs:label"]?.[0]?.value ||
                  classId}
              </Text>
              <Text fontSize="sm" color="gray.500" fontFamily="mono">
                {owlClass.uri}
              </Text>
            </VStack>
          </HStack>
          <HStack>
            {hasChanges && (
              <>
                <Badge colorPalette="orange" variant="subtle">
                  Unsaved changes
                </Badge>
                <Button size="sm" variant="ghost" onClick={handleReset}>
                  Reset
                </Button>
                <Button size="sm" colorPalette="primary" onClick={handleSave}>
                  <Save size={14} style={{ marginRight: "4px" }} />
                  Save
                </Button>
              </>
            )}
            <Button
              size="sm"
              colorPalette="red"
              variant="ghost"
              onClick={() => onDeleteClass(classId)}
              ml={hasChanges ? 2 : 0}
            >
              <Trash2 size={14} style={{ marginRight: "4px" }} />
              Delete
            </Button>
          </HStack>
        </HStack>
      </Box>

      {/* Form Content */}
      <Box flex="1" overflow="auto" p={6}>
        <VStack align="stretch" spacing={6} maxW="600px">
          {/* Basic Information */}
          <VStack align="stretch" spacing={4}>
            <Text fontSize="md" fontWeight="semibold" color="gray.700">
              Basic Information
            </Text>

            <MultiLanguageLabels
              label="Label"
              labels={labels}
              onLabelsChange={setLabels}
            />

            <Field.Root>
              <Field.Label>Description</Field.Label>
              <Textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Brief description of what this class represents..."
                rows={3}
              />
              <Text fontSize="xs" color="gray.500" mt={1}>
                A brief description explaining the purpose and scope of this
                class
              </Text>
            </Field.Root>
          </VStack>

          <Separator />

          {/* Technical Information */}
          <VStack align="stretch" spacing={4}>
            <Text fontSize="md" fontWeight="semibold" color="gray.700">
              Technical Details
            </Text>

            <Field.Root>
              <Field.Label>URI</Field.Label>
              <Input
                value={owlClass.uri}
                readOnly
                bg="gray.50"
                color="gray.600"
                fontFamily="mono"
                fontSize="sm"
              />
              <Text fontSize="xs" color="gray.500" mt={1}>
                Unique identifier for this class (read-only)
              </Text>
            </Field.Root>

            <Field.Root>
              <Field.Label>Type</Field.Label>
              <Input
                value="owl:Class"
                readOnly
                bg="gray.50"
                color="gray.600"
                fontFamily="mono"
                fontSize="sm"
              />
              <Text fontSize="xs" color="gray.500" mt={1}>
                OWL class type (read-only)
              </Text>
            </Field.Root>

            <Field.Root>
              <Field.Label>Class ID</Field.Label>
              <Input
                value={classId}
                readOnly
                bg="gray.50"
                color="gray.600"
                fontFamily="mono"
                fontSize="sm"
              />
              <Text fontSize="xs" color="gray.500" mt={1}>
                Internal identifier used in the ontology structure (read-only)
              </Text>
            </Field.Root>
          </VStack>

          <Separator />

          {/* Relationships */}
          <VStack align="stretch" spacing={4}>
            <Text fontSize="md" fontWeight="semibold" color="gray.700">
              Relationships
            </Text>

            <VStack align="stretch" spacing={1}>
              <SelectField
                label="Subclass Of (rdfs:subClassOf)"
                items={[
                  {
                    value: "",
                    label: "None (top-level class)",
                    description: (
                      <SelectOptionText>
                        None (top-level class)
                      </SelectOptionText>
                    ),
                  },
                  ...Object.entries(ontology.classes)
                    .filter(([id]) => id !== classId) // Don't allow self-reference
                    .map(([id, owlClass]) => ({
                      value: id,
                      label: owlClass["rdfs:label"]?.[0]?.value || id,
                      description: (
                        <SelectOptionText>
                          {owlClass["rdfs:label"]?.[0]?.value || id}
                        </SelectOptionText>
                      ),
                    })),
                ]}
                value={[subClassOf]}
                onValueChange={(values) => setSubClassOf(values[0] || "")}
              />
              <Text fontSize="xs" color="gray.500" mt={1}>
                Choose a parent class to create a subclass relationship. Leave
                empty for top-level classes.
              </Text>
            </VStack>

            {/* Equivalent Classes */}
            <VStack align="stretch" spacing={3}>
              <Text fontSize="sm" fontWeight="medium" color="gray.700">
                Equivalent Classes (owl:equivalentClass)
              </Text>

              <VStack align="stretch" spacing={2}>
                {equivalentClasses.map((equivalentClassId, index) => (
                  <HStack key={index} spacing={2}>
                    <SelectField
                      items={[
                        {
                          value: "",
                          label: "Select class...",
                          description: (
                            <SelectOptionText>
                              Select class...
                            </SelectOptionText>
                          ),
                        },
                        ...Object.entries(ontology.classes)
                          .filter(
                            ([id]) =>
                              id !== classId &&
                              !equivalentClasses.includes(id),
                          )
                          .map(([id, owlClass]) => ({
                            value: id,
                            label: owlClass["rdfs:label"]?.[0]?.value || id,
                            description: (
                              <SelectOptionText>
                                {owlClass["rdfs:label"]?.[0]?.value || id}
                              </SelectOptionText>
                            ),
                          })),
                      ]}
                      value={[equivalentClassId]}
                      onValueChange={(values) => {
                        const value = values[0] || "";
                        const newEquivalentClasses = [...equivalentClasses];
                        newEquivalentClasses[index] = value;
                        setEquivalentClasses(newEquivalentClasses);
                      }}
                      placeholder="Select equivalent class"
                    />
                    <Button
                      size="sm"
                      variant="ghost"
                      colorPalette="red"
                      onClick={() => {
                        const newEquivalentClasses = equivalentClasses.filter(
                          (_, i) => i !== index,
                        );
                        setEquivalentClasses(newEquivalentClasses);
                      }}
                    >
                      <Trash2 size={14} />
                    </Button>
                  </HStack>
                ))}

                <Button
                  size="sm"
                  variant="ghost"
                  colorPalette="blue"
                  onClick={() =>
                    setEquivalentClasses([...equivalentClasses, ""])
                  }
                  alignSelf="flex-start"
                >
                  <Link size={14} style={{ marginRight: "4px" }} />
                  Add Equivalent Class
                </Button>

                <Text fontSize="xs" color="gray.500">
                  Classes that represent the same concept and have identical
                  sets of instances
                </Text>
              </VStack>
            </VStack>

            {/* Disjoint Classes */}
            <VStack align="stretch" spacing={3}>
              <Text fontSize="sm" fontWeight="medium" color="gray.700">
                Disjoint Classes (owl:disjointWith)
              </Text>

              <VStack align="stretch" spacing={2}>
                {disjointClasses.map((disjointClassId, index) => (
                  <HStack key={index} spacing={2}>
                    <SelectField
                      items={[
                        {
                          value: "",
                          label: "Select class...",
                          description: (
                            <SelectOptionText>
                              Select class...
                            </SelectOptionText>
                          ),
                        },
                        ...Object.entries(ontology.classes)
                          .filter(
                            ([id]) =>
                              id !== classId && !disjointClasses.includes(id),
                          )
                          .map(([id, owlClass]) => ({
                            value: id,
                            label: owlClass["rdfs:label"]?.[0]?.value || id,
                            description: (
                              <SelectOptionText>
                                {owlClass["rdfs:label"]?.[0]?.value || id}
                              </SelectOptionText>
                            ),
                          })),
                      ]}
                      value={[disjointClassId]}
                      onValueChange={(values) => {
                        const value = values[0] || "";
                        const newDisjointClasses = [...disjointClasses];
                        newDisjointClasses[index] = value;
                        setDisjointClasses(newDisjointClasses);
                      }}
                      placeholder="Select disjoint class"
                    />
                    <Button
                      size="sm"
                      variant="ghost"
                      colorPalette="red"
                      onClick={() => {
                        const newDisjointClasses = disjointClasses.filter(
                          (_, i) => i !== index,
                        );
                        setDisjointClasses(newDisjointClasses);
                      }}
                    >
                      <Trash2 size={14} />
                    </Button>
                  </HStack>
                ))}

                <Button
                  size="sm"
                  variant="ghost"
                  colorPalette="blue"
                  onClick={() => setDisjointClasses([...disjointClasses, ""])}
                  alignSelf="flex-start"
                >
                  <AlertTriangle size={14} style={{ marginRight: "4px" }} />
                  Add Disjoint Class
                </Button>

                <Text fontSize="xs" color="gray.500">
                  Classes that cannot share any instances (mutually exclusive)
                </Text>
              </VStack>
            </VStack>
          </VStack>

          <Separator />

          {/* Properties with this class as domain */}
          <VStack align="stretch" spacing={4}>
            <Text fontSize="md" fontWeight="semibold" color="gray.700">
              Properties with this class as domain
            </Text>

            {(() => {
              const objectPropsWithDomain = Object.entries(
                ontology.objectProperties,
              ).filter(([, prop]) => prop["rdfs:domain"] === classId);
              const datatypePropsWithDomain = Object.entries(
                ontology.datatypeProperties,
              ).filter(([, prop]) => prop["rdfs:domain"] === classId);
              const allPropsWithDomain = [
                ...objectPropsWithDomain,
                ...datatypePropsWithDomain,
              ];

              if (allPropsWithDomain.length === 0) {
                return (
                  <Box p={4} bg="gray.50" borderRadius="md">
                    <VStack spacing={2}>
                      <Text fontSize="sm" color="gray.600" fontWeight="medium">
                        No properties use this class as domain
                      </Text>
                      <Text fontSize="xs" color="gray.500" textAlign="center">
                        Properties that specify this class as their domain will
                        appear here
                      </Text>
                    </VStack>
                  </Box>
                );
              }

              return (
                <VStack align="stretch" spacing={2}>
                  {objectPropsWithDomain.map(([propId, prop]) => (
                    <Box
                      key={propId}
                      p={3}
                      bg="white"
                      borderWidth="1px"
                      borderRadius="md"
                      cursor="pointer"
                      _hover={{ bg: "blue.50", borderColor: "blue.300" }}
                      onClick={() => {
                        // Navigate to property editor
                        if (onNavigateToProperty) {
                          onNavigateToProperty(propId, "objectProperty");
                        }
                      }}
                    >
                      <HStack spacing={3}>
                        <Link size={16} color="#666" />
                        <VStack align="start" spacing={1} flex="1">
                          <Text
                            fontSize="sm"
                            fontWeight="medium"
                            color="blue.800"
                          >
                            {prop["rdfs:label"]?.[0]?.value || propId}
                          </Text>
                          <HStack spacing={2}>
                            <Badge
                              colorPalette="blue"
                              variant="subtle"
                              size="sm"
                            >
                              Object Property
                            </Badge>
                            {prop["rdfs:range"] && (
                              <Text fontSize="xs" color="gray.600">
                                →{" "}
                                {ontology.classes[prop["rdfs:range"]]?.[
                                  "rdfs:label"
                                ]?.[0]?.value || prop["rdfs:range"]}
                              </Text>
                            )}
                          </HStack>
                          {prop["rdfs:comment"] && (
                            <Text fontSize="xs" color="gray.500">
                              {prop["rdfs:comment"]}
                            </Text>
                          )}
                        </VStack>
                      </HStack>
                    </Box>
                  ))}
                  {datatypePropsWithDomain.map(([propId, prop]) => (
                    <Box
                      key={propId}
                      p={3}
                      bg="white"
                      borderWidth="1px"
                      borderRadius="md"
                      cursor="pointer"
                      _hover={{ bg: "purple.50", borderColor: "purple.300" }}
                      onClick={() => {
                        // Navigate to property editor
                        if (onNavigateToProperty) {
                          onNavigateToProperty(propId, "datatypeProperty");
                        }
                      }}
                    >
                      <HStack spacing={3}>
                        <Type size={16} color="#666" />
                        <VStack align="start" spacing={1} flex="1">
                          <Text
                            fontSize="sm"
                            fontWeight="medium"
                            color="purple.800"
                          >
                            {prop["rdfs:label"]?.[0]?.value || propId}
                          </Text>
                          <HStack spacing={2}>
                            <Badge
                              colorPalette="purple"
                              variant="subtle"
                              size="sm"
                            >
                              Datatype Property
                            </Badge>
                            {prop["rdfs:range"] && (
                              <Text fontSize="xs" color="gray.600">
                                : {prop["rdfs:range"]}
                              </Text>
                            )}
                          </HStack>
                          {prop["rdfs:comment"] && (
                            <Text fontSize="xs" color="gray.500">
                              {prop["rdfs:comment"]}
                            </Text>
                          )}
                        </VStack>
                      </HStack>
                    </Box>
                  ))}
                </VStack>
              );
            })()}
          </VStack>
        </VStack>
      </Box>
    </Box>
  );
};
