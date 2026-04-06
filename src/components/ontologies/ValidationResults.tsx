import React from "react";
import { Box, Text, Alert, HStack, Badge } from "@chakra-ui/react";
import { AlertTriangle, X } from "lucide-react";
import { ValidationResult } from "../../utils/skos-validation";

interface ValidationResultsProps {
  validation: ValidationResult | null;
  maxErrors?: number;
  maxWarnings?: number;
}

export const ValidationResults: React.FC<ValidationResultsProps> = ({
  validation,
  maxErrors = 3,
  maxWarnings = 2,
}) => {
  if (!validation) return null;

  return (
    <Box>
      <Text fontSize="sm" fontWeight="bold" mb={2}>
        Validation Results
      </Text>

      {validation.errors.length > 0 && (
        <Alert.Root status="error" mb={2}>
          <Alert.Indicator />
          <Alert.Content>
            <Alert.Description>
              {validation.errors.length} error(s) found
            </Alert.Description>
          </Alert.Content>
        </Alert.Root>
      )}

      {validation.warnings.length > 0 && (
        <Alert.Root status="warning" mb={2}>
          <Alert.Indicator />
          <Alert.Content>
            <Alert.Description>
              {validation.warnings.length} warning(s) found
            </Alert.Description>
          </Alert.Content>
        </Alert.Root>
      )}

      {validation.isValid && (
        <Alert.Root status="success" mb={2}>
          <Alert.Indicator />
          <Alert.Content>
            <Alert.Description>SKOS validation passed</Alert.Description>
          </Alert.Content>
        </Alert.Root>
      )}

      {/* Show first few errors/warnings */}
      {[
        ...validation.errors.slice(0, maxErrors),
        ...validation.warnings.slice(0, maxWarnings),
      ].map((issue, index) => {
        const isError = issue.type === "error";
        const IconComponent = isError ? X : AlertTriangle;
        const iconColor = isError ? "red.500" : "orange.500";
        // Use a more unique key combining type, index, and partial message
        const uniqueKey = `${issue.type}-${index}-${issue.message?.substring(0, 10) || "no-msg"}`;

        return (
          <Box
            key={uniqueKey}
            p={2}
            bg="gray.50"
            _dark={{ bg: "gray.700" }}
            borderRadius="md"
            mb={1}
            fontSize="sm"
          >
            <HStack spacing={2} align="flex-start">
              <Box
                color={iconColor}
                flexShrink={0}
                aria-label={isError ? "Error" : "Warning"}
              >
                <IconComponent size={16} />
              </Box>
              <Text flex="1">{issue.message || "No message provided"}</Text>
              {issue.conceptId && (
                <Badge size="xs" variant="outline">
                  {issue.conceptId}
                </Badge>
              )}
            </HStack>
          </Box>
        );
      })}
    </Box>
  );
};
