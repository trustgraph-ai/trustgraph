import React, { useState, useRef } from "react";
import {
  Box,
  VStack,
  HStack,
  Text,
  Button,
  Field,
  Textarea,
  Alert,
  Badge,
  RadioGroup,
} from "@chakra-ui/react";
import { Upload, X, FileText, AlertTriangle } from "lucide-react";
import SelectField from "../common/SelectField";
import SelectOptionText from "../common/SelectOptionText";
import { useOntologies, Ontology } from "@trustgraph/react-state";
import {
  OntologyImporter,
  ImportFormat,
  ImportOptions,
} from "./OntologyImporter";
import { useNotification } from "@trustgraph/react-state";

interface ImportDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onImported?: (ontologyId: string) => void;
}

export const ImportDialog: React.FC<ImportDialogProps> = ({
  isOpen,
  onClose,
  onImported,
}) => {
  const [format, setFormat] = useState<ImportFormat | "auto">("auto");
  const [importMode, setImportMode] = useState<"new" | "merge" | "overwrite">(
    "new",
  );
  const [ontologyId, setOntologyId] = useState("");
  const [fileContent, setFileContent] = useState("");
  const [fileName, setFileName] = useState<string | null>(null);
  const [isImporting, setIsImporting] = useState(false);
  const [detectedFormat, setDetectedFormat] = useState<ImportFormat | null>(
    null,
  );
  const [parseError, setParseError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { createOntology, updateOntology, ontologies } = useOntologies();
  const notify = useNotification();

  const formatOptions = [
    {
      value: "auto",
      label: "Auto-detect",
      description: <SelectOptionText>Auto-detect</SelectOptionText>,
    },
    {
      value: "owl",
      label: "OWL/XML (.owl)",
      description: <SelectOptionText>OWL/XML (.owl)</SelectOptionText>,
    },
    {
      value: "rdf",
      label: "RDF/XML (.rdf)",
      description: <SelectOptionText>RDF/XML (.rdf)</SelectOptionText>,
    },
    {
      value: "turtle",
      label: "Turtle (.ttl)",
      description: <SelectOptionText>Turtle (.ttl)</SelectOptionText>,
    },
  ];

  const handleFileSelect = async (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setFileName(file.name);
    setParseError(null);

    const reader = new FileReader();
    reader.onload = async (e) => {
      const content = e.target?.result as string;
      setFileContent(content);

      // Auto-detect format
      if (format === "auto") {
        const detected = OntologyImporter.detectFormat(content);
        if (detected) {
          setDetectedFormat(detected);
        } else {
          setParseError(
            "Could not detect file format. Please select the format manually.",
          );
        }
      }

      // Generate ontology ID from filename
      const baseId = file.name
        .replace(/\.(owl|rdf|ttl|xml)$/i, "")
        .toLowerCase()
        .replace(/[^a-z0-9-]/g, "-");
      setOntologyId(baseId);
    };

    reader.onerror = () => {
      setParseError("Failed to read file");
    };

    reader.readAsText(file);
  };

  const handleTextPaste = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const content = e.target.value;
    setFileContent(content);
    setFileName(null);
    setParseError(null);

    // Auto-detect format
    if (format === "auto" && content.trim()) {
      const detected = OntologyImporter.detectFormat(content);
      if (detected) {
        setDetectedFormat(detected);
      } else {
        setParseError(
          "Could not detect format. Please select the format manually.",
        );
      }
    }
  };

  const handleImport = async () => {
    if (!fileContent) {
      notify.warning("Please select a file or paste content to import");
      return;
    }

    if (!ontologyId) {
      notify.warning("Please provide an ontology ID");
      return;
    }

    setIsImporting(true);
    setParseError(null);

    try {
      const importFormat = format === "auto" ? detectedFormat : format;
      if (!importFormat) {
        throw new Error("Could not determine import format");
      }

      const options: ImportOptions = {
        format: importFormat as ImportFormat,
        mergeWithExisting: importMode === "merge",
        overwriteExisting: importMode === "overwrite",
      };

      const importedOntology = await OntologyImporter.import(
        fileContent,
        options,
      );

      // Check if ontology ID already exists
      const existingOntology = ontologies.find((ont) => ont[0] === ontologyId);

      if (existingOntology && importMode === "new") {
        notify.warning(
          `Ontology with ID "${ontologyId}" already exists. Use merge or overwrite mode.`,
        );
        setIsImporting(false);
        return;
      }

      if (importMode === "merge" && existingOntology) {
        // Merge with existing ontology
        const existingData = existingOntology[1];
        const mergedOntology: Ontology = {
          metadata: {
            ...existingData.metadata,
            ...importedOntology.metadata,
            modified: new Date().toISOString(),
          },
          classes: {
            ...existingData.classes,
            ...importedOntology.classes,
          },
          objectProperties: {
            ...existingData.objectProperties,
            ...importedOntology.objectProperties,
          },
          datatypeProperties: {
            ...existingData.datatypeProperties,
            ...importedOntology.datatypeProperties,
          },
        };

        updateOntology({
          id: ontologyId,
          ontology: mergedOntology,
          onSuccess: () => {
            notify.success(`Successfully merged ontology "${ontologyId}"`);
            onClose();
            if (onImported) {
              onImported(ontologyId);
            }
          },
        });
      } else {
        // Create new or overwrite
        createOntology({
          id: ontologyId,
          ontology: importedOntology,
          onSuccess: () => {
            notify.success(`Successfully imported ontology "${ontologyId}"`);
            onClose();
            if (onImported) {
              onImported(ontologyId);
            }
          },
        });
      }
    } catch (error) {
      console.error("Import failed:", error);
      setParseError(error instanceof Error ? error.message : "Import failed");
      notify.error(
        `Failed to import ontology: ${error instanceof Error ? error.message : "Unknown error"}`,
      );
    } finally {
      setIsImporting(false);
    }
  };

  const handleReset = () => {
    setFileContent("");
    setFileName(null);
    setDetectedFormat(null);
    setParseError(null);
    setOntologyId("");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  if (!isOpen) return null;

  return (
    <Box
      position="fixed"
      top="0"
      left="0"
      right="0"
      bottom="0"
      bg="blackAlpha.600"
      display="flex"
      alignItems="center"
      justifyContent="center"
      zIndex="modal"
    >
      <Box
        bg="white"
        borderRadius="md"
        boxShadow="xl"
        w="600px"
        maxW="90vw"
        maxH="90vh"
        overflow="auto"
      >
        {/* Header */}
        <Box p={4} borderBottomWidth="1px">
          <HStack justify="space-between" align="center">
            <Text fontSize="lg" fontWeight="semibold">
              Import Ontology
            </Text>
            <Button variant="ghost" size="sm" onClick={onClose}>
              <X size={16} />
            </Button>
          </HStack>
        </Box>

        {/* Content */}
        <Box p={6}>
          <VStack align="stretch" spacing={6}>
            {/* File Input Section */}
            <VStack align="stretch" spacing={4}>
              <Text fontSize="md" fontWeight="medium">
                Select File or Paste Content
              </Text>

              <Box
                p={4}
                borderWidth="2px"
                borderStyle="dashed"
                borderColor="gray.300"
                borderRadius="md"
                textAlign="center"
                cursor="pointer"
                _hover={{ borderColor: "blue.400", bg: "blue.50" }}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".owl,.rdf,.ttl,.xml"
                  onChange={handleFileSelect}
                  style={{ display: "none" }}
                />
                <VStack spacing={2}>
                  <Upload size={32} color="#718096" />
                  <Text fontSize="sm" color="gray.600">
                    Click to select file or drag and drop
                  </Text>
                  <Text fontSize="xs" color="gray.500">
                    Supports: OWL/XML (.owl), RDF/XML (.rdf), Turtle (.ttl)
                  </Text>
                  {fileName && (
                    <HStack>
                      <FileText size={16} />
                      <Text fontSize="sm" fontWeight="medium">
                        {fileName}
                      </Text>
                    </HStack>
                  )}
                </VStack>
              </Box>

              <Text fontSize="sm" color="gray.600" textAlign="center">
                OR
              </Text>

              <Field.Root>
                <Field.Label>Paste Ontology Content</Field.Label>
                <Textarea
                  value={fileContent}
                  onChange={handleTextPaste}
                  placeholder="Paste OWL, RDF, or Turtle content here..."
                  rows={6}
                  fontFamily="mono"
                  fontSize="sm"
                />
              </Field.Root>
            </VStack>

            {/* Format Selection */}
            <Field.Root required>
              <Field.Label>Import Format</Field.Label>
              <SelectField
                items={formatOptions}
                value={[format]}
                onValueChange={(values) =>
                  setFormat((values[0] || "auto") as ImportFormat | "auto")
                }
              />
              {detectedFormat && format === "auto" && (
                <HStack mt={2}>
                  <Badge colorPalette="green" variant="subtle">
                    Auto-detected: {detectedFormat.toUpperCase()}
                  </Badge>
                </HStack>
              )}
            </Field.Root>

            {/* Import Mode */}
            <Field.Root required>
              <Field.Label>Import Mode</Field.Label>
              <RadioGroup.Root
                value={importMode}
                onValueChange={(e) =>
                  setImportMode(e.value as "new" | "merge" | "overwrite")
                }
              >
                <VStack align="stretch" spacing={2}>
                  <RadioGroup.Item value="new">
                    <RadioGroup.ItemControl />
                    <RadioGroup.ItemText>
                      <Text fontSize="sm" fontWeight="medium">
                        Create New
                      </Text>
                      <Text fontSize="xs" color="gray.600">
                        Create a new ontology (fails if ID exists)
                      </Text>
                    </RadioGroup.ItemText>
                  </RadioGroup.Item>

                  <RadioGroup.Item value="merge">
                    <RadioGroup.ItemControl />
                    <RadioGroup.ItemText>
                      <Text fontSize="sm" fontWeight="medium">
                        Merge with Existing
                      </Text>
                      <Text fontSize="xs" color="gray.600">
                        Merge classes and properties with existing ontology
                      </Text>
                    </RadioGroup.ItemText>
                  </RadioGroup.Item>

                  <RadioGroup.Item value="overwrite">
                    <RadioGroup.ItemControl />
                    <RadioGroup.ItemText>
                      <Text fontSize="sm" fontWeight="medium">
                        Overwrite Existing
                      </Text>
                      <Text fontSize="xs" color="gray.600">
                        Replace existing ontology completely
                      </Text>
                    </RadioGroup.ItemText>
                  </RadioGroup.Item>
                </VStack>
              </RadioGroup.Root>
            </Field.Root>

            {/* Ontology ID */}
            <Field.Root required>
              <Field.Label>
                Ontology ID
                <Field.RequiredIndicator />
              </Field.Label>
              <input
                type="text"
                value={ontologyId}
                onChange={(e) => setOntologyId(e.target.value)}
                placeholder="my-ontology"
                className="chakra-input"
                style={{
                  width: "100%",
                  padding: "8px 12px",
                  borderRadius: "6px",
                  border: "1px solid #e2e8f0",
                }}
              />
              <Text fontSize="xs" color="gray.500" mt={1}>
                Unique identifier for the ontology (lowercase, no spaces)
              </Text>
            </Field.Root>

            {/* Parse Error */}
            {parseError && (
              <Alert.Root status="error">
                <Alert.Indicator>
                  <AlertTriangle size={16} />
                </Alert.Indicator>
                <Alert.Content>
                  <Alert.Title>Import Error</Alert.Title>
                  <Alert.Description>{parseError}</Alert.Description>
                </Alert.Content>
              </Alert.Root>
            )}

            {/* Summary */}
            {fileContent && !parseError && (
              <Box
                p={3}
                bg="blue.50"
                borderRadius="md"
                borderLeftWidth="3px"
                borderLeftColor="blue.500"
              >
                <VStack align="stretch" spacing={1}>
                  <Text fontSize="sm" fontWeight="medium" color="blue.800">
                    Ready to Import
                  </Text>
                  <Text fontSize="xs" color="blue.700">
                    • Format:{" "}
                    {format === "auto"
                      ? detectedFormat || "detecting..."
                      : format.toUpperCase()}
                  </Text>
                  <Text fontSize="xs" color="blue.700">
                    • Mode:{" "}
                    {importMode === "new"
                      ? "Create new"
                      : importMode === "merge"
                        ? "Merge"
                        : "Overwrite"}
                  </Text>
                  <Text fontSize="xs" color="blue.700">
                    • Content size: {fileContent.length.toLocaleString()}{" "}
                    characters
                  </Text>
                </VStack>
              </Box>
            )}
          </VStack>
        </Box>

        {/* Footer */}
        <Box p={4} borderTopWidth="1px" bg="gray.50">
          <HStack justify="space-between">
            <Button
              size="sm"
              variant="ghost"
              onClick={handleReset}
              disabled={isImporting || !fileContent}
            >
              Clear
            </Button>
            <HStack spacing={3}>
              <Button variant="ghost" onClick={onClose} disabled={isImporting}>
                Cancel
              </Button>
              <Button
                colorPalette="primary"
                onClick={handleImport}
                loading={isImporting}
                disabled={!fileContent || !ontologyId || isImporting}
              >
                <Upload size={16} style={{ marginRight: "8px" }} />
                {isImporting ? "Importing..." : "Import"}
              </Button>
            </HStack>
          </HStack>
        </Box>
      </Box>
    </Box>
  );
};
