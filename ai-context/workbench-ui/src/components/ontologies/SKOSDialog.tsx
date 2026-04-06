import React, { useState, useRef } from "react";
import {
  Dialog,
  Portal,
  Button,
  VStack,
  HStack,
  Text,
  Textarea,
  Tabs,
  Box,
  Badge,
  Separator,
  IconButton,
} from "@chakra-ui/react";
import { Download, Upload, Copy, Check } from "lucide-react";
import { useNotification } from "@trustgraph/react-state";
import { Ontology } from "@trustgraph/react-state";
import { serializeToSKOS, parseFromSKOS } from "../../utils/skos";
import {
  validateOntology,
  ValidationResult,
} from "../../utils/skos-validation";
import {
  exportOntology,
  EXPORT_FORMATS,
  ExportFormat,
} from "../../utils/export-formats";
import SelectField from "../common/SelectField";
import { ValidationResults } from "./ValidationResults";

interface SKOSDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  ontology?: Ontology;
  mode: "export" | "import";
  onImport?: (ontology: Ontology, ontologyId: string) => void;
}

export const SKOSDialog: React.FC<SKOSDialogProps> = ({
  open,
  onOpenChange,
  ontology,
  mode,
  onImport,
}) => {
  const [format, setFormat] = useState<ExportFormat>("skos-rdf");
  const [content, setContent] = useState("");
  const [importId, setImportId] = useState("");
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [copied, setCopied] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const notify = useNotification();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleExport = React.useCallback(() => {
    if (!ontology) return;

    try {
      let exported: string;

      if (format === "skos-rdf" || format === "skos-turtle") {
        // Use SKOS serializer for SKOS formats
        const skosFormat = format === "skos-rdf" ? "rdf" : "turtle";
        exported = serializeToSKOS(ontology, skosFormat as "rdf" | "turtle");
      } else {
        // Use additional export formats
        exported = exportOntology(ontology, format);
      }

      setContent(exported);

      // Also validate the ontology (only for SKOS formats)
      if (format === "skos-rdf" || format === "skos-turtle") {
        const validationResult = validateOntology(ontology);
        setValidation(validationResult);
      } else {
        setValidation(null); // No SKOS validation for non-SKOS formats
      }
    } catch (error) {
      notify.error(
        `Export failed: ${error instanceof Error ? error.message : "Unknown error"}`,
      );
    }
  }, [ontology, format, notify]);

  const handleImport = async () => {
    if (!content.trim() || !importId.trim()) {
      notify.error("Please provide both content and ontology ID");
      return;
    }

    setIsProcessing(true);
    try {
      let imported: Ontology;

      if (format === "skos-rdf" || format === "skos-turtle") {
        // Use SKOS parser for SKOS formats
        const skosFormat = format === "skos-rdf" ? "rdf" : "turtle";
        imported = await parseFromSKOS(
          content,
          importId,
          skosFormat as "rdf" | "turtle",
        );

        // Validate SKOS ontology
        const validationResult = validateOntology(imported);
        setValidation(validationResult);

        if (validationResult.errors.length > 0) {
          notify.error(
            `Import validation failed with ${validationResult.errors.length} errors`,
          );
          return;
        }
      } else if (format === "json") {
        // Parse JSON format
        imported = JSON.parse(content);
      } else {
        notify.error("Import is only supported for SKOS and JSON formats");
        return;
      }

      if (onImport) {
        onImport(imported, importId);
        notify.success("Ontology imported successfully");
        onOpenChange(false);
      }
    } catch (error) {
      notify.error(
        `Import failed: ${error instanceof Error ? error.message : "Unknown error"}`,
      );
    } finally {
      setIsProcessing(false);
    }
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      notify.success("SKOS content copied to clipboard");
    } catch {
      notify.error("Failed to copy to clipboard");
    }
  };

  const handleDownload = () => {
    if (!content || !ontology) return;

    const formatInfo = EXPORT_FORMATS[format];
    const extension = formatInfo.extension;
    const mimeType = formatInfo.mimeType;

    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${ontology.metadata.name.replace(/\s+/g, "-")}.${extension}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    notify.success(`${formatInfo.name} file downloaded`);
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      setContent(text);

      // Auto-detect format from file extension
      if (file.name.endsWith(".ttl")) {
        setFormat("skos-turtle");
      } else if (file.name.endsWith(".rdf") || file.name.endsWith(".xml")) {
        setFormat("skos-rdf");
      } else if (file.name.endsWith(".json")) {
        setFormat("json");
      }

      // Set default import ID from filename
      const baseName = file.name.replace(/\.(ttl|rdf|xml)$/, "");
      setImportId(baseName.replace(/[^a-zA-Z0-9-]/g, "-").toLowerCase());
    };
    reader.readAsText(file);
  };

  React.useEffect(() => {
    if (open && mode === "export" && ontology) {
      handleExport();
    }
  }, [open, mode, ontology, handleExport]);

  React.useEffect(() => {
    // Reset state when dialog opens
    if (open) {
      setContent("");
      setImportId("");
      setValidation(null);
      setCopied(false);
      setIsProcessing(false);
    }
  }, [open]);

  return (
    <Dialog.Root
      open={open}
      onOpenChange={(details) => onOpenChange(details.open)}
    >
      <Portal>
        <Dialog.Backdrop />
        <Dialog.Positioner>
          <Dialog.Content maxW="6xl" maxH="90vh">
            <Dialog.Header>
              <Dialog.Title>
                {mode === "export" ? "Export Ontology" : "Import Ontology"}
              </Dialog.Title>
            </Dialog.Header>

            <Dialog.Body overflowY="auto">
              <VStack gap={4} align="stretch">
                {/* Format Selection */}
                <SelectField
                  label={mode === "export" ? "Export Format" : "Import Format"}
                  items={Object.entries(EXPORT_FORMATS)
                    .filter(
                      ([key]) =>
                        mode === "export" ||
                        key === "skos-rdf" ||
                        key === "skos-turtle" ||
                        key === "json",
                    )
                    .map(([key, info]) => ({
                      value: key,
                      label: info.name,
                      description: info.description,
                    }))}
                  value={[format]}
                  onValueChange={(values) => {
                    setFormat((values[0] || "skos-ttl") as ExportFormat);
                    // Re-export with new format if dialog is in export mode
                    if (mode === "export" && ontology) {
                      setTimeout(() => handleExport(), 0);
                    }
                  }}
                />

                {mode === "import" && (
                  <>
                    <Box>
                      <Text fontSize="sm" fontWeight="bold" mb={2}>
                        Import Source
                      </Text>
                      <HStack>
                        <Button
                          variant="outline"
                          onClick={() => fileInputRef.current?.click()}
                          size="sm"
                        >
                          <Upload size={16} />
                          Choose File
                        </Button>
                        <Text fontSize="sm" color="fg.muted">
                          Or paste{" "}
                          {format.includes("skos") ? "SKOS" : "ontology"}{" "}
                          content below
                        </Text>
                      </HStack>
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept=".rdf,.xml,.ttl,.json"
                        style={{ display: "none" }}
                        onChange={handleFileUpload}
                      />
                    </Box>

                    <Box>
                      <Text fontSize="sm" fontWeight="bold" mb={2}>
                        Ontology ID
                      </Text>
                      <Textarea
                        value={importId}
                        onChange={(e) => setImportId(e.target.value)}
                        placeholder="Enter unique ontology ID (e.g., 'risk-categories')"
                        rows={1}
                        resize="none"
                      />
                    </Box>
                  </>
                )}

                <Separator />

                <Tabs.Root defaultValue="content">
                  <Tabs.List>
                    <Tabs.Trigger value="content">
                      {format.includes("skos")
                        ? "SKOS Content"
                        : `${EXPORT_FORMATS[format].name} Content`}
                    </Tabs.Trigger>
                    {validation && (
                      <Tabs.Trigger value="validation">
                        Validation
                        <Badge
                          ml={2}
                          colorPalette={validation.isValid ? "primary" : "red"}
                          size="xs"
                        >
                          {validation.errors.length > 0
                            ? validation.errors.length
                            : "✓"}
                        </Badge>
                      </Tabs.Trigger>
                    )}
                  </Tabs.List>

                  <Tabs.Content value="content">
                    <VStack gap={3} align="stretch">
                      {mode === "export" && (
                        <HStack justify="space-between">
                          <Text fontSize="sm" color="fg.muted">
                            Generated {EXPORT_FORMATS[format].name}
                          </Text>
                          <HStack>
                            <IconButton
                              aria-label="Copy"
                              size="sm"
                              variant="outline"
                              onClick={handleCopy}
                              disabled={!content}
                            >
                              {copied ? (
                                <Check size={16} />
                              ) : (
                                <Copy size={16} />
                              )}
                            </IconButton>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={handleDownload}
                              disabled={!content}
                            >
                              <Download size={16} />
                              Download
                            </Button>
                          </HStack>
                        </HStack>
                      )}

                      <Textarea
                        value={content}
                        onChange={(e) => setContent(e.target.value)}
                        placeholder={
                          mode === "import"
                            ? `Paste ${format.includes("skos") ? "SKOS" : "ontology"} content here...`
                            : `${EXPORT_FORMATS[format].name} content will appear here`
                        }
                        rows={20}
                        fontFamily="mono"
                        fontSize="sm"
                        readOnly={mode === "export"}
                      />
                    </VStack>
                  </Tabs.Content>

                  <Tabs.Content value="validation">
                    <ValidationResults validation={validation} />
                  </Tabs.Content>
                </Tabs.Root>
              </VStack>
            </Dialog.Body>

            <Dialog.Footer>
              <HStack gap={3}>
                <Button variant="ghost" onClick={() => onOpenChange(false)}>
                  {mode === "export" ? "Close" : "Cancel"}
                </Button>

                {mode === "export" && (
                  <Button colorPalette="primary" onClick={handleExport}>
                    Regenerate
                  </Button>
                )}

                {mode === "import" && (
                  <Button
                    colorPalette="primary"
                    onClick={handleImport}
                    disabled={
                      !content.trim() || !importId.trim() || isProcessing
                    }
                    loading={isProcessing}
                  >
                    Import Ontology
                  </Button>
                )}
              </HStack>
            </Dialog.Footer>

            <Dialog.CloseTrigger />
          </Dialog.Content>
        </Dialog.Positioner>
      </Portal>
    </Dialog.Root>
  );
};
