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
  Badge,
  Alert,
} from "@chakra-ui/react";
import { Save } from "lucide-react";
import { OntologyMetadata } from "@trustgraph/react-state";
import { NamespacePrefixEditor } from "./NamespacePrefixEditor";

interface MetadataEditorProps {
  metadata: OntologyMetadata;
  onUpdateMetadata: (metadata: OntologyMetadata) => void;
  hasClasses?: boolean;
  hasProperties?: boolean;
}

export const MetadataEditor: React.FC<MetadataEditorProps> = ({
  metadata,
  onUpdateMetadata,
  hasClasses = false,
  hasProperties = false,
}) => {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [version, setVersion] = useState("");
  const [creator, setCreator] = useState("");
  const [namespace, setNamespace] = useState("");
  const [namespaces, setNamespaces] = useState<Record<string, string>>({});
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    // Initialize form with current values
    setName(metadata.name || "");
    setDescription(metadata.description || "");
    setVersion(metadata.version || "1.0");
    setCreator(metadata.creator || "");
    setNamespace(metadata.namespace || "");
    setNamespaces(metadata.namespaces || {});
    setHasChanges(false);
  }, [metadata]);

  useEffect(() => {
    // Check for changes
    const nameChanged = name !== (metadata.name || "");
    const descriptionChanged = description !== (metadata.description || "");
    const versionChanged = version !== (metadata.version || "1.0");
    const creatorChanged = creator !== (metadata.creator || "");
    const namespaceChanged = namespace !== (metadata.namespace || "");
    const namespacesChanged =
      JSON.stringify(namespaces) !== JSON.stringify(metadata.namespaces || {});

    setHasChanges(
      nameChanged ||
        descriptionChanged ||
        versionChanged ||
        creatorChanged ||
        namespaceChanged ||
        namespacesChanged,
    );
  }, [name, description, version, creator, namespace, namespaces, metadata]);

  const handleSave = () => {
    const updatedMetadata: OntologyMetadata = {
      ...metadata,
      name: name.trim(),
      description: description.trim(),
      version: version.trim() || "1.0",
      creator: creator.trim(),
      namespace: namespace.trim(),
      namespaces,
      modified: new Date().toISOString(),
    };

    onUpdateMetadata(updatedMetadata);
    setHasChanges(false);
  };

  const handleReset = () => {
    setName(metadata.name || "");
    setDescription(metadata.description || "");
    setVersion(metadata.version || "1.0");
    setCreator(metadata.creator || "");
    setNamespace(metadata.namespace || "");
    setNamespaces(metadata.namespaces || {});
    setHasChanges(false);
  };

  const isValidURI = (uri: string): boolean => {
    try {
      new URL(uri);
      return uri.endsWith("/") || uri.endsWith("#");
    } catch {
      return false;
    }
  };

  const namespaceValid = !namespace || isValidURI(namespace);
  const hasContent = hasClasses || hasProperties;

  return (
    <Box h="100%" display="flex" flexDirection="column">
      {/* Header */}
      <Box p={6} borderBottomWidth="1px" bg="white">
        <HStack justify="space-between" align="center">
          <VStack align="start" spacing={1}>
            <Text fontSize="lg" fontWeight="semibold">
              Ontology Metadata
            </Text>
            <Text fontSize="sm" color="gray.600">
              Configure basic information about this ontology
            </Text>
          </VStack>
          <HStack>
            {hasChanges && (
              <>
                <Badge colorPalette="orange" variant="subtle">
                  Unsaved changes
                </Badge>
                <Button size="sm" variant="ghost" onClick={handleReset}>
                  Reset
                </Button>
                <Button
                  size="sm"
                  colorPalette="primary"
                  onClick={handleSave}
                  disabled={!namespaceValid}
                >
                  <Save size={14} style={{ marginRight: "4px" }} />
                  Save
                </Button>
              </>
            )}
          </HStack>
        </HStack>
      </Box>

      {/* Form Content */}
      <Box flex="1" overflow="auto" p={6}>
        <VStack align="stretch" spacing={6} maxW="600px">
          {/* Namespace Warning */}
          {hasContent && hasChanges && namespace !== metadata.namespace && (
            <Alert.Root status="warning">
              <Alert.Indicator />
              <Alert.Content>
                <Alert.Title>Namespace Change Warning</Alert.Title>
                <Alert.Description>
                  Changing the namespace will affect all existing class and
                  property URIs. This may break external references to your
                  ontology.
                </Alert.Description>
              </Alert.Content>
            </Alert.Root>
          )}

          {/* Basic Information */}
          <VStack align="stretch" spacing={4}>
            <Text fontSize="md" fontWeight="semibold" color="gray.700">
              Basic Information
            </Text>

            <Field.Root required>
              <Field.Label>
                Ontology Name
                <Field.RequiredIndicator />
              </Field.Label>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="My Domain Ontology"
              />
              <Text fontSize="xs" color="gray.500" mt={1}>
                A human-readable name for this ontology
              </Text>
            </Field.Root>

            <Field.Root>
              <Field.Label>Description</Field.Label>
              <Textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="A comprehensive ontology for modeling..."
                rows={3}
              />
              <Text fontSize="xs" color="gray.500" mt={1}>
                Brief description of the ontology's purpose and scope
              </Text>
            </Field.Root>

            <HStack spacing={4}>
              <Field.Root flex="1">
                <Field.Label>Version</Field.Label>
                <Input
                  value={version}
                  onChange={(e) => setVersion(e.target.value)}
                  placeholder="1.0"
                />
              </Field.Root>

              <Field.Root flex="1">
                <Field.Label>Creator</Field.Label>
                <Input
                  value={creator}
                  onChange={(e) => setCreator(e.target.value)}
                  placeholder="data-architect-001"
                />
              </Field.Root>
            </HStack>
          </VStack>

          {/* Technical Details */}
          <VStack align="stretch" spacing={4}>
            <Text fontSize="md" fontWeight="semibold" color="gray.700">
              Technical Details
            </Text>

            <Field.Root required invalid={!namespaceValid}>
              <Field.Label>
                Ontology URI
                <Field.RequiredIndicator />
              </Field.Label>
              <Input
                value={namespace}
                onChange={(e) => setNamespace(e.target.value)}
                placeholder="http://example.org/myontology#"
              />
              <Text
                fontSize="xs"
                color={namespaceValid ? "gray.500" : "red.500"}
                mt={1}
              >
                {namespaceValid
                  ? "The ontology's own identifier (must end with # or /)"
                  : "Invalid URI format - must be a valid URL ending with # or /"}
              </Text>
            </Field.Root>

            <Box mt={4}>
              <NamespacePrefixEditor
                namespaces={namespaces}
                onChange={setNamespaces}
              />
              <Text fontSize="xs" color="gray.500" mt={2}>
                Namespace prefixes are used to abbreviate URIs when exporting
                to Turtle format
              </Text>
            </Box>

            <Field.Root>
              <Field.Label>Created</Field.Label>
              <Input
                value={new Date(metadata.created).toLocaleString()}
                readOnly
                bg="gray.50"
                color="gray.600"
              />
            </Field.Root>

            <Field.Root>
              <Field.Label>Last Modified</Field.Label>
              <Input
                value={new Date(metadata.modified).toLocaleString()}
                readOnly
                bg="gray.50"
                color="gray.600"
              />
            </Field.Root>
          </VStack>

          {/* Future Features */}
          <VStack align="stretch" spacing={4}>
            <Text fontSize="md" fontWeight="semibold" color="gray.700">
              Advanced Settings
            </Text>

            <Box p={3} bg="gray.50" borderRadius="md">
              <VStack spacing={1}>
                <Text fontSize="sm" color="gray.600" fontWeight="medium">
                  Coming Soon
                </Text>
                <Text fontSize="xs" color="gray.500" textAlign="center">
                  • Import declarations (owl:imports)
                  <br />• Ontology annotations
                </Text>
              </VStack>
            </Box>
          </VStack>
        </VStack>
      </Box>
    </Box>
  );
};
