import React, { useState, useEffect } from "react";
import {
  Box,
  VStack,
  HStack,
  Text,
  Input,
  Textarea,
  Button,
  Badge,
  Separator,
  Fieldset,
} from "@chakra-ui/react";
import { Save, X, FileCode } from "lucide-react";
import { FlowClassDefinition } from "@trustgraph/react-state";

interface FlowClassEditPanelProps {
  flowClass: FlowClassDefinition;
  onSave?: (flowClass: FlowClassDefinition) => void;
  onCancel?: () => void;
  isLoading?: boolean;
}

const FlowClassEditPanel: React.FC<FlowClassEditPanelProps> = ({
  flowClass,
  onSave,
  onCancel,
  isLoading = false,
}) => {
  const [description, setDescription] = useState(flowClass.description || "");
  const [tags, setTags] = useState((flowClass.tags || []).join(", "));

  useEffect(() => {
    setDescription(flowClass.description || "");
    setTags((flowClass.tags || []).join(", "));
  }, [flowClass]);

  const handleSave = () => {
    const updatedFlowClass: FlowClassDefinition = {
      ...flowClass,
      description: description.trim() || undefined,
      tags: tags
        .split(",")
        .map((tag) => tag.trim())
        .filter((tag) => tag.length > 0)
        .slice(0, 10), // Limit to 10 tags
    };

    onSave?.(updatedFlowClass);
  };

  const hasChanges =
    description !== (flowClass.description || "") ||
    tags !== (flowClass.tags || []).join(", ");

  const classCount = Object.keys(flowClass.class || {}).length;
  const flowCount = Object.keys(flowClass.flow || {}).length;
  const interfaceCount = Object.keys(flowClass.interfaces || {}).length;

  return (
    <Box
      position="fixed"
      bottom={0}
      left={0}
      right={0}
      bg="bg.default"
      borderTop="1px solid"
      borderColor="border.muted"
      boxShadow="0 -4px 6px -1px rgba(0, 0, 0, 0.1)"
      zIndex={50}
      p={6}
      maxH="50vh"
      overflowY="auto"
    >
      <VStack gap={4} align="stretch" maxW="1200px" mx="auto">
        {/* Header */}
        <HStack justify="space-between" align="center">
          <HStack gap={3}>
            <FileCode size={20} />
            <Text fontSize="lg" fontWeight="semibold">
              Edit Flow Class: {flowClass.id}
            </Text>
          </HStack>
          <HStack gap={2}>
            <Button
              variant="outline"
              size="sm"
              onClick={onCancel}
              disabled={isLoading}
            >
              <X size={16} />
              Cancel
            </Button>
            <Button
              variant="solid"
              colorPalette="blue"
              size="sm"
              onClick={handleSave}
              disabled={!hasChanges || isLoading}
              loading={isLoading}
            >
              <Save size={16} />
              Save Changes
            </Button>
          </HStack>
        </HStack>

        <Separator />

        <HStack gap={6} align="stretch">
          {/* Left Column - Basic Info */}
          <VStack gap={4} align="stretch" flex={1}>
            <Fieldset.Root>
              <Fieldset.Legend>Basic Information</Fieldset.Legend>
              <Fieldset.Content>
                <VStack gap={3} align="stretch">
                  <Box>
                    <Text fontSize="sm" fontWeight="medium" mb={2}>
                      Description
                    </Text>
                    <Textarea
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      placeholder="Enter flow class description..."
                      rows={3}
                      resize="none"
                    />
                  </Box>

                  <Box>
                    <Text fontSize="sm" fontWeight="medium" mb={2}>
                      Tags{" "}
                      <Text as="span" color="fg.muted">
                        (comma-separated)
                      </Text>
                    </Text>
                    <Input
                      value={tags}
                      onChange={(e) => setTags(e.target.value)}
                      placeholder="rag, document-processing, llm..."
                    />
                  </Box>
                </VStack>
              </Fieldset.Content>
            </Fieldset.Root>
          </VStack>

          {/* Right Column - Statistics */}
          <VStack gap={4} align="stretch" minW="300px">
            <Fieldset.Root>
              <Fieldset.Legend>Flow Class Statistics</Fieldset.Legend>
              <Fieldset.Content>
                <VStack gap={3} align="stretch">
                  <HStack justify="space-between">
                    <Text fontSize="sm">Class Processors:</Text>
                    <Badge colorPalette="blue">{classCount}</Badge>
                  </HStack>

                  <HStack justify="space-between">
                    <Text fontSize="sm">Flow Processors:</Text>
                    <Badge colorPalette="green">{flowCount}</Badge>
                  </HStack>

                  <HStack justify="space-between">
                    <Text fontSize="sm">Interfaces:</Text>
                    <Badge colorPalette="purple">{interfaceCount}</Badge>
                  </HStack>

                  <HStack justify="space-between">
                    <Text fontSize="sm">Total Components:</Text>
                    <Badge colorPalette="gray">
                      {classCount + flowCount + interfaceCount}
                    </Badge>
                  </HStack>
                </VStack>
              </Fieldset.Content>
            </Fieldset.Root>

            {/* Preview of current tags */}
            {flowClass.tags && flowClass.tags.length > 0 && (
              <Box>
                <Text fontSize="sm" fontWeight="medium" mb={2}>
                  Current Tags
                </Text>
                <HStack gap={1} flexWrap="wrap">
                  {flowClass.tags.map((tag, index) => (
                    <Badge
                      key={index}
                      colorPalette="gray"
                      size="sm"
                      variant="outline"
                    >
                      {tag}
                    </Badge>
                  ))}
                </HStack>
              </Box>
            )}
          </VStack>
        </HStack>
      </VStack>
    </Box>
  );
};

export default FlowClassEditPanel;
