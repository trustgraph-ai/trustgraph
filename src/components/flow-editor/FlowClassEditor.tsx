import React from "react";
import { Box, VStack, Heading, Text, Button } from "@chakra-ui/react";
import { Construction } from "lucide-react";

interface FlowClassEditorProps {
  flowClassId?: string;
  onClose?: () => void;
}

export const FlowClassEditor: React.FC<FlowClassEditorProps> = ({
  flowClassId,
  onClose,
}) => {
  return (
    <Box
      h="100vh"
      bg="bg.subtle"
      display="flex"
      alignItems="center"
      justifyContent="center"
    >
      <VStack
        gap={6}
        p={8}
        bg="bg"
        borderRadius="lg"
        boxShadow="lg"
        maxW="600px"
      >
        <Construction size={48} color="var(--colors-fg-muted)" />

        <VStack gap={2} textAlign="center">
          <Heading size="xl">Flow Class Editor</Heading>
          <Text color="fg.muted" fontSize="lg">
            Under Construction
          </Text>
        </VStack>

        <VStack gap={3} textAlign="center">
          <Text color="fg.subtle">
            The Flow Class Editor is being rebuilt for a better experience.
          </Text>
          {flowClassId && (
            <Text fontSize="sm" color="fg.muted">
              Flow Class ID: <code>{flowClassId}</code>
            </Text>
          )}
        </VStack>

        {onClose && (
          <Button onClick={onClose} variant="outline" size="lg">
            Go Back
          </Button>
        )}
      </VStack>
    </Box>
  );
};
