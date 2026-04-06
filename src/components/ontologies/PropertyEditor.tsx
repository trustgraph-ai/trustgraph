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
  Checkbox,
} from "@chakra-ui/react";
import SelectField from "../common/SelectField";
import SelectOptionText from "../common/SelectOptionText";
import XSDDatatypeSelector from "./XSDDatatypeSelector";
import { Link, Type, Save, Trash2 } from "lucide-react";
import {
  OWLObjectProperty,
  OWLDatatypeProperty,
  Ontology,
} from "@trustgraph/react-state";

interface PropertyEditorProps {
  propertyId: string;
  property: OWLObjectProperty | OWLDatatypeProperty;
  propertyType: "object" | "datatype";
  ontology: Ontology;
  onUpdateProperty: (
    propertyId: string,
    updatedProperty: OWLObjectProperty | OWLDatatypeProperty,
    type: "object" | "datatype",
  ) => void;
  onDeleteProperty: (propertyId: string, type: "object" | "datatype") => void;
}

export const PropertyEditor: React.FC<PropertyEditorProps> = ({
  propertyId,
  property,
  propertyType,
  ontology,
  onUpdateProperty,
  onDeleteProperty,
}) => {
  const [label, setLabel] = useState("");
  const [comment, setComment] = useState("");
  const [domain, setDomain] = useState("");
  const [range, setRange] = useState("");
  const [isFunctional, setIsFunctional] = useState(false);
  const [minCardinality, setMinCardinality] = useState<number | undefined>(
    undefined,
  );
  const [maxCardinality, setMaxCardinality] = useState<number | undefined>(
    undefined,
  );
  const [exactCardinality, setExactCardinality] = useState<number | undefined>(
    undefined,
  );
  const [inverseOf, setInverseOf] = useState("");
  const [isInverseFunctional, setIsInverseFunctional] = useState(false);
  const [subPropertyOf, setSubPropertyOf] = useState("");
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    // Initialize form with current values
    const currentLabel = property["rdfs:label"]?.[0]?.value || "";
    const currentComment = property["rdfs:comment"] || "";
    const currentDomain = property["rdfs:domain"] || "";
    const currentRange = property["rdfs:range"] || "";
    const currentIsFunctional = property["owl:functionalProperty"] || false;
    const currentMinCardinality = property["owl:minCardinality"];
    const currentMaxCardinality = property["owl:maxCardinality"];
    const currentExactCardinality = property["owl:cardinality"];
    const currentInverseOf =
      (propertyType === "object" &&
        (property as OWLObjectProperty)["owl:inverseOf"]) ||
      "";
    const currentIsInverseFunctional =
      (propertyType === "object" &&
        (property as OWLObjectProperty)["owl:inverseFunctionalProperty"]) ||
      false;
    const currentSubPropertyOf = property["rdfs:subPropertyOf"] || "";

    setLabel(currentLabel);
    setComment(currentComment);
    setDomain(currentDomain);
    setRange(currentRange);
    setIsFunctional(currentIsFunctional);
    setMinCardinality(currentMinCardinality);
    setMaxCardinality(currentMaxCardinality);
    setExactCardinality(currentExactCardinality);
    setInverseOf(currentInverseOf);
    setIsInverseFunctional(currentIsInverseFunctional);
    setSubPropertyOf(currentSubPropertyOf);
    setHasChanges(false);
  }, [propertyId, property, propertyType]);

  useEffect(() => {
    // Check for changes
    const currentLabel = property["rdfs:label"]?.[0]?.value || "";
    const currentComment = property["rdfs:comment"] || "";
    const currentDomain = property["rdfs:domain"] || "";
    const currentRange = property["rdfs:range"] || "";
    const currentIsFunctional = property["owl:functionalProperty"] || false;
    const currentMinCardinality = property["owl:minCardinality"];
    const currentMaxCardinality = property["owl:maxCardinality"];
    const currentExactCardinality = property["owl:cardinality"];
    const currentInverseOf =
      (propertyType === "object" &&
        (property as OWLObjectProperty)["owl:inverseOf"]) ||
      "";
    const currentIsInverseFunctional =
      (propertyType === "object" &&
        (property as OWLObjectProperty)["owl:inverseFunctionalProperty"]) ||
      false;
    const currentSubPropertyOf = property["rdfs:subPropertyOf"] || "";

    const labelChanged = label !== currentLabel;
    const commentChanged = comment !== currentComment;
    const domainChanged = domain !== currentDomain;
    const rangeChanged = range !== currentRange;
    const functionalChanged = isFunctional !== currentIsFunctional;
    const minCardinalityChanged = minCardinality !== currentMinCardinality;
    const maxCardinalityChanged = maxCardinality !== currentMaxCardinality;
    const exactCardinalityChanged =
      exactCardinality !== currentExactCardinality;
    const inverseOfChanged = inverseOf !== currentInverseOf;
    const inverseFunctionalChanged =
      isInverseFunctional !== currentIsInverseFunctional;
    const subPropertyOfChanged = subPropertyOf !== currentSubPropertyOf;

    setHasChanges(
      labelChanged ||
        commentChanged ||
        domainChanged ||
        rangeChanged ||
        functionalChanged ||
        minCardinalityChanged ||
        maxCardinalityChanged ||
        exactCardinalityChanged ||
        inverseOfChanged ||
        inverseFunctionalChanged ||
        subPropertyOfChanged,
    );
  }, [
    label,
    comment,
    domain,
    range,
    isFunctional,
    minCardinality,
    maxCardinality,
    exactCardinality,
    inverseOf,
    isInverseFunctional,
    subPropertyOf,
    property,
    propertyType,
  ]);

  const handleSave = () => {
    const baseUpdatedProperty = {
      ...property,
      "rdfs:label": label.trim() ? [{ value: label.trim(), lang: "en" }] : [],
      "rdfs:comment": comment.trim(),
      "rdfs:domain": domain.trim() || undefined,
      "rdfs:range": range.trim() || undefined,
      "owl:functionalProperty": isFunctional || undefined,
      "owl:minCardinality": minCardinality || undefined,
      "owl:maxCardinality": maxCardinality || undefined,
      "owl:cardinality": exactCardinality || undefined,
      "rdfs:subPropertyOf": subPropertyOf.trim() || undefined,
    };

    let updatedProperty;
    if (propertyType === "object") {
      updatedProperty = {
        ...baseUpdatedProperty,
        "owl:inverseOf": inverseOf.trim() || undefined,
        "owl:inverseFunctionalProperty": isInverseFunctional || undefined,
      } as OWLObjectProperty;
    } else {
      updatedProperty = baseUpdatedProperty as OWLDatatypeProperty;
    }

    onUpdateProperty(propertyId, updatedProperty, propertyType);
    setHasChanges(false);
  };

  const handleReset = () => {
    const currentLabel = property["rdfs:label"]?.[0]?.value || "";
    const currentComment = property["rdfs:comment"] || "";
    const currentDomain = property["rdfs:domain"] || "";
    const currentRange = property["rdfs:range"] || "";
    const currentIsFunctional = property["owl:functionalProperty"] || false;
    const currentMinCardinality = property["owl:minCardinality"];
    const currentMaxCardinality = property["owl:maxCardinality"];
    const currentExactCardinality = property["owl:cardinality"];
    const currentInverseOf =
      (propertyType === "object" &&
        (property as OWLObjectProperty)["owl:inverseOf"]) ||
      "";
    const currentIsInverseFunctional =
      (propertyType === "object" &&
        (property as OWLObjectProperty)["owl:inverseFunctionalProperty"]) ||
      false;
    const currentSubPropertyOf = property["rdfs:subPropertyOf"] || "";

    setLabel(currentLabel);
    setComment(currentComment);
    setDomain(currentDomain);
    setRange(currentRange);
    setIsFunctional(currentIsFunctional);
    setMinCardinality(currentMinCardinality);
    setMaxCardinality(currentMaxCardinality);
    setExactCardinality(currentExactCardinality);
    setInverseOf(currentInverseOf);
    setIsInverseFunctional(currentIsInverseFunctional);
    setSubPropertyOf(currentSubPropertyOf);
    setHasChanges(false);
  };

  // Get available classes for domain/range selection
  const classOptions = [
    {
      value: "",
      label: "None",
      description: <SelectOptionText>None</SelectOptionText>,
    },
    ...Object.entries(ontology.classes).map(([id, owlClass]) => ({
      value: id,
      label: owlClass["rdfs:label"]?.[0]?.value || id,
      description: (
        <SelectOptionText>
          {owlClass["rdfs:label"]?.[0]?.value || id}
        </SelectOptionText>
      ),
    })),
  ];

  // Get available properties for subPropertyOf and inverseOf
  const sameTypePropertyOptions = [
    {
      value: "",
      label: "None",
      description: <SelectOptionText>None</SelectOptionText>,
    },
    ...Object.entries(
      propertyType === "object"
        ? ontology.objectProperties
        : ontology.datatypeProperties,
    )
      .filter(([id]) => id !== propertyId) // Don't allow self-reference
      .map(([id, prop]) => ({
        value: id,
        label: prop["rdfs:label"]?.[0]?.value || id,
        description: (
          <SelectOptionText>
            {prop["rdfs:label"]?.[0]?.value || id}
          </SelectOptionText>
        ),
      })),
  ];

  const objectPropertyOptions = [
    {
      value: "",
      label: "None",
      description: <SelectOptionText>None</SelectOptionText>,
    },
    ...Object.entries(ontology.objectProperties)
      .filter(([id]) => id !== propertyId) // Don't allow self-reference
      .map(([id, prop]) => ({
        value: id,
        label: prop["rdfs:label"]?.[0]?.value || id,
        description: (
          <SelectOptionText>
            {prop["rdfs:label"]?.[0]?.value || id}
          </SelectOptionText>
        ),
      })),
  ];

  return (
    <Box h="100%" display="flex" flexDirection="column">
      {/* Header */}
      <Box p={4} borderBottomWidth="1px">
        <HStack justify="space-between" align="center">
          <HStack>
            {propertyType === "object" ? (
              <Link size={20} color="#666" />
            ) : (
              <Type size={20} color="#666" />
            )}
            <VStack align="start" spacing={0}>
              <Text fontSize="lg" fontWeight="semibold">
                {property["rdfs:label"]?.[0]?.value || propertyId}
              </Text>
              <Text fontSize="sm" color="gray.500" fontFamily="mono">
                {property.uri}
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
              onClick={() => onDeleteProperty(propertyId, propertyType)}
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

            <Field.Root required>
              <Field.Label>
                Label
                <Field.RequiredIndicator />
              </Field.Label>
              <Input
                value={label}
                onChange={(e) => setLabel(e.target.value)}
                placeholder="Human-readable property name"
              />
              <Text fontSize="xs" color="gray.500" mt={1}>
                The preferred human-readable name for this property
              </Text>
            </Field.Root>

            <Field.Root>
              <Field.Label>Description</Field.Label>
              <Textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Brief description of what this property represents..."
                rows={3}
              />
              <Text fontSize="xs" color="gray.500" mt={1}>
                A brief description explaining the purpose and scope of this
                property
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
                value={property.uri}
                readOnly
                bg="gray.50"
                color="gray.600"
                fontFamily="mono"
                fontSize="sm"
              />
              <Text fontSize="xs" color="gray.500" mt={1}>
                Unique identifier for this property (read-only)
              </Text>
            </Field.Root>

            <Field.Root>
              <Field.Label>Type</Field.Label>
              <Input
                value={property.type}
                readOnly
                bg="gray.50"
                color="gray.600"
                fontFamily="mono"
                fontSize="sm"
              />
              <Text fontSize="xs" color="gray.500" mt={1}>
                OWL property type (read-only)
              </Text>
            </Field.Root>

            <Field.Root>
              <Field.Label>Property ID</Field.Label>
              <Input
                value={propertyId}
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

          {/* Domain and Range */}
          <VStack align="stretch" spacing={4}>
            <Text fontSize="md" fontWeight="semibold" color="gray.700">
              Domain and Range
            </Text>

            <VStack align="stretch" spacing={1}>
              <SelectField
                label="Domain (rdfs:domain)"
                items={classOptions}
                value={[domain]}
                onValueChange={(values) => setDomain(values[0] || "")}
              />
              <Text fontSize="xs" color="gray.500" mt={1}>
                The class that can have this property. Leave empty if any class
                can have this property.
              </Text>
            </VStack>

            <VStack align="stretch" spacing={1}>
              {propertyType === "object" ? (
                <SelectField
                  label="Range (rdfs:range)"
                  items={classOptions}
                  value={[range]}
                  onValueChange={(values) => setRange(values[0] || "")}
                />
              ) : (
                <XSDDatatypeSelector
                  label="Range (rdfs:range)"
                  value={range}
                  onValueChange={setRange}
                />
              )}
              <Text fontSize="xs" color="gray.500" mt={1}>
                {propertyType === "object"
                  ? "The class that this property points to."
                  : "The datatype of values for this property."}
              </Text>
            </VStack>
          </VStack>

          <Separator />

          {/* Advanced Properties and Constraints */}
          <VStack align="stretch" spacing={4}>
            <Text fontSize="md" fontWeight="semibold" color="gray.700">
              Advanced Properties and Constraints
            </Text>

            {/* Property Hierarchy */}
            <VStack align="stretch" spacing={1}>
              <SelectField
                label="Subproperty Of (rdfs:subPropertyOf)"
                items={sameTypePropertyOptions}
                value={[subPropertyOf]}
                onValueChange={(values) => setSubPropertyOf(values[0] || "")}
              />
              <Text fontSize="xs" color="gray.500" mt={1}>
                Make this property a specialization of another property
              </Text>
            </VStack>

            {/* Object Property Specific Features */}
            {propertyType === "object" && (
              <>
                <VStack align="stretch" spacing={1}>
                  <SelectField
                    label="Inverse Of (owl:inverseOf)"
                    items={objectPropertyOptions}
                    value={[inverseOf]}
                    onValueChange={(values) => setInverseOf(values[0] || "")}
                  />
                  <Text fontSize="xs" color="gray.500" mt={1}>
                    Specify the inverse relationship (e.g., 'hasParent' inverse
                    of 'hasChild')
                  </Text>
                </VStack>

                <Checkbox.Root
                  checked={isInverseFunctional}
                  onCheckedChange={(e) => setIsInverseFunctional(!!e.checked)}
                >
                  <Checkbox.HiddenInput />
                  <Checkbox.Control />
                  <Checkbox.Label>Inverse Functional Property</Checkbox.Label>
                </Checkbox.Root>
                <Text fontSize="xs" color="gray.500" mt={-2}>
                  At most one subject can have any given object (unique
                  identifier property)
                </Text>
              </>
            )}

            {/* Property Characteristics */}
            <VStack align="stretch" spacing={3}>
              <Text fontSize="sm" fontWeight="medium" color="gray.700">
                Property Characteristics
              </Text>

              <Checkbox.Root
                checked={isFunctional}
                onCheckedChange={(e) => setIsFunctional(!!e.checked)}
              >
                <Checkbox.HiddenInput />
                <Checkbox.Control />
                <Checkbox.Label>Functional Property</Checkbox.Label>
              </Checkbox.Root>
              <Text fontSize="xs" color="gray.500" mt={-2}>
                Each subject can have at most one value for this property
              </Text>
            </VStack>

            {/* Cardinality Constraints */}
            <VStack align="stretch" spacing={4}>
              <Text fontSize="sm" fontWeight="medium" color="gray.700">
                Cardinality Constraints
              </Text>

              <HStack spacing={4}>
                <Field.Root flex="1">
                  <Field.Label>Min Cardinality</Field.Label>
                  <Input
                    type="number"
                    min="0"
                    value={minCardinality || ""}
                    onChange={(e) =>
                      setMinCardinality(
                        e.target.value ? parseInt(e.target.value) : undefined,
                      )
                    }
                    placeholder="No minimum"
                  />
                </Field.Root>

                <Field.Root flex="1">
                  <Field.Label>Max Cardinality</Field.Label>
                  <Input
                    type="number"
                    min="0"
                    value={maxCardinality || ""}
                    onChange={(e) =>
                      setMaxCardinality(
                        e.target.value ? parseInt(e.target.value) : undefined,
                      )
                    }
                    placeholder="No maximum"
                  />
                </Field.Root>
              </HStack>

              <Field.Root>
                <Field.Label>Exact Cardinality</Field.Label>
                <Input
                  type="number"
                  min="0"
                  value={exactCardinality || ""}
                  onChange={(e) =>
                    setExactCardinality(
                      e.target.value ? parseInt(e.target.value) : undefined,
                    )
                  }
                  placeholder="No exact requirement"
                />
                <Text fontSize="xs" color="gray.500" mt={1}>
                  If specified, overrides min/max cardinality (exactly N values
                  required)
                </Text>
              </Field.Root>
            </VStack>
          </VStack>
        </VStack>
      </Box>
    </Box>
  );
};
