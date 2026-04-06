import React, { useState } from "react";
import {
  Box,
  VStack,
  HStack,
  Text,
  Button,
  Checkbox,
  Field,
} from "@chakra-ui/react";
import { Download, X } from "lucide-react";
import SelectField from "../common/SelectField";
import SelectOptionText from "../common/SelectOptionText";
import { Ontology } from "@trustgraph/react-state";
import { OntologyExporter, ExportOptions } from "./OntologyExporter";
import { useNotification } from "@trustgraph/react-state";

interface ExportDialogProps {
  ontology: Ontology;
  isOpen: boolean;
  onClose: () => void;
}

export const ExportDialog: React.FC<ExportDialogProps> = ({
  ontology,
  isOpen,
  onClose,
}) => {
  const [format, setFormat] = useState<ExportOptions["format"]>("owl");
  const [includeComments, setIncludeComments] = useState(true);
  const [includeNamespaces, setIncludeNamespaces] = useState(true);
  const [isExporting, setIsExporting] = useState(false);
  const notify = useNotification();

  const formatOptions = [
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

  const handleExport = async () => {
    setIsExporting(true);

    try {
      const options: ExportOptions = {
        format,
        includeComments,
        includeNamespaces,
      };

      const content = OntologyExporter.export(ontology, options);
      const filename = `${ontology.metadata.name || "ontology"}${OntologyExporter.getFileExtension(format)}`;
      const mimeType = OntologyExporter.getMimeType(format);

      OntologyExporter.downloadFile(content, filename, mimeType);

      notify.success(
        `Successfully exported "${ontology.metadata.name}" as ${format.toUpperCase()}`,
      );

      // Close dialog after successful export
      onClose();
    } catch (error) {
      console.error("Export failed:", error);
      notify.error(
        `Failed to export ontology: ${error instanceof Error ? error.message : "Unknown error"}`,
      );
    } finally {
      setIsExporting(false);
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
        w="500px"
        maxW="90vw"
        maxH="90vh"
        overflow="auto"
      >
        {/* Header */}
        <Box p={4} borderBottomWidth="1px">
          <HStack justify="space-between" align="center">
            <Text fontSize="lg" fontWeight="semibold">
              Export Ontology
            </Text>
            <Button variant="ghost" size="sm" onClick={onClose}>
              <X size={16} />
            </Button>
          </HStack>
        </Box>

        {/* Content */}
        <Box p={6}>
          <VStack align="stretch" spacing={6}>
            <VStack align="stretch" spacing={4}>
              <Text fontSize="md" fontWeight="medium">
                Export "{ontology.metadata.name}"
              </Text>
              <Text fontSize="sm" color="gray.600">
                Choose your export format and options below. Your ontology will
                be downloaded as a file.
              </Text>
            </VStack>

            <VStack align="stretch" spacing={4}>
              <Field.Root required>
                <Field.Label>Export Format</Field.Label>
                <SelectField
                  items={formatOptions}
                  value={[format]}
                  onValueChange={(values) =>
                    setFormat((values[0] || "ttl") as ExportOptions["format"])
                  }
                />
                <Text fontSize="xs" color="gray.500" mt={1}>
                  Choose the format for your exported ontology file
                </Text>
              </Field.Root>

              <VStack align="stretch" spacing={3}>
                <Text fontSize="sm" fontWeight="medium">
                  Export Options
                </Text>

                <Checkbox.Root
                  checked={includeComments}
                  onCheckedChange={(e) => setIncludeComments(!!e.checked)}
                >
                  <Checkbox.HiddenInput />
                  <Checkbox.Control />
                  <Checkbox.Label>
                    Include comments and descriptions
                  </Checkbox.Label>
                </Checkbox.Root>

                <Checkbox.Root
                  checked={includeNamespaces}
                  onCheckedChange={(e) => setIncludeNamespaces(!!e.checked)}
                >
                  <Checkbox.HiddenInput />
                  <Checkbox.Control />
                  <Checkbox.Label>
                    Include namespace declarations
                  </Checkbox.Label>
                </Checkbox.Root>
              </VStack>

              <Box
                p={3}
                bg="blue.50"
                borderRadius="md"
                borderLeftWidth="3px"
                borderLeftColor="blue.500"
              >
                <VStack align="stretch" spacing={1}>
                  <Text fontSize="sm" fontWeight="medium" color="blue.800">
                    Export Summary
                  </Text>
                  <Text fontSize="xs" color="blue.700">
                    • {Object.keys(ontology.classes).length} classes
                  </Text>
                  <Text fontSize="xs" color="blue.700">
                    • {Object.keys(ontology.objectProperties).length} object
                    properties
                  </Text>
                  <Text fontSize="xs" color="blue.700">
                    • {Object.keys(ontology.datatypeProperties).length}{" "}
                    datatype properties
                  </Text>
                </VStack>
              </Box>
            </VStack>
          </VStack>
        </Box>

        {/* Footer */}
        <Box p={4} borderTopWidth="1px" bg="gray.50">
          <HStack justify="flex-end" spacing={3}>
            <Button variant="ghost" onClick={onClose} disabled={isExporting}>
              Cancel
            </Button>
            <Button
              colorPalette="primary"
              onClick={handleExport}
              loading={isExporting}
              disabled={isExporting}
            >
              <Download size={16} style={{ marginRight: "8px" }} />
              {isExporting ? "Exporting..." : "Export"}
            </Button>
          </HStack>
        </Box>
      </Box>
    </Box>
  );
};
