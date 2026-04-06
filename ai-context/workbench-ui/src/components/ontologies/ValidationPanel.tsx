import React from "react";
import {
  Box,
  VStack,
  HStack,
  Text,
  Badge,
  Button,
  Separator,
  Alert,
} from "@chakra-ui/react";
import {
  AlertTriangle,
  CheckCircle,
  Info,
  XCircle,
  Hash,
  Link,
  Type,
} from "lucide-react";
import { ValidationResult, ValidationIssue } from "./OntologyValidator";

interface ValidationPanelProps {
  validationResult: ValidationResult;
  onNavigateToItem?: (
    itemId: string,
    itemType: "class" | "objectProperty" | "datatypeProperty",
  ) => void;
  onClose: () => void;
}

export const ValidationPanel: React.FC<ValidationPanelProps> = ({
  validationResult,
  onNavigateToItem,
  onClose,
}) => {
  const { isValid, issues, summary } = validationResult;

  const getIssueIcon = (type: ValidationIssue["type"]) => {
    switch (type) {
      case "error":
        return <XCircle size={14} color="#E53E3E" />;
      case "warning":
        return <AlertTriangle size={14} color="#DD6B20" />;
      case "info":
        return <Info size={14} color="#3182CE" />;
    }
  };

  const getIssueColor = (type: ValidationIssue["type"]) => {
    switch (type) {
      case "error":
        return "red";
      case "warning":
        return "orange";
      case "info":
        return "blue";
    }
  };

  const getItemIcon = (itemType?: ValidationIssue["itemType"]) => {
    switch (itemType) {
      case "class":
        return <Hash size={12} color="#666" />;
      case "objectProperty":
        return <Link size={12} color="#666" />;
      case "datatypeProperty":
        return <Type size={12} color="#666" />;
      default:
        return null;
    }
  };

  const handleNavigateToItem = (issue: ValidationIssue) => {
    if (issue.itemId && issue.itemType && onNavigateToItem) {
      onNavigateToItem(issue.itemId, issue.itemType);
    }
  };

  if (issues.length === 0) {
    return (
      <Box
        p={4}
        borderWidth="1px"
        borderRadius="md"
        bg="green.50"
        borderColor="green.200"
      >
        <HStack spacing={3}>
          <CheckCircle size={20} color="#38A169" />
          <VStack align="start" spacing={1}>
            <Text fontWeight="semibold" color="green.800">
              Ontology is valid
            </Text>
            <Text fontSize="sm" color="green.600">
              No validation issues found. Your ontology follows best practices.
            </Text>
          </VStack>
        </HStack>
      </Box>
    );
  }

  return (
    <Box borderWidth="1px" borderRadius="md" bg="white" overflow="hidden">
      {/* Header */}
      <Box p={4} bg="gray.50" borderBottomWidth="1px">
        <HStack justify="space-between" align="center">
          <VStack align="start" spacing={1}>
            <Text fontWeight="semibold" fontSize="lg">
              Validation Results
            </Text>
            <HStack spacing={4}>
              {summary.errors > 0 && (
                <HStack spacing={1}>
                  <XCircle size={14} color="#E53E3E" />
                  <Text fontSize="sm" color="red.600">
                    {summary.errors} error{summary.errors !== 1 ? "s" : ""}
                  </Text>
                </HStack>
              )}
              {summary.warnings > 0 && (
                <HStack spacing={1}>
                  <AlertTriangle size={14} color="#DD6B20" />
                  <Text fontSize="sm" color="orange.600">
                    {summary.warnings} warning
                    {summary.warnings !== 1 ? "s" : ""}
                  </Text>
                </HStack>
              )}
              {summary.info > 0 && (
                <HStack spacing={1}>
                  <Info size={14} color="#3182CE" />
                  <Text fontSize="sm" color="blue.600">
                    {summary.info} suggestion{summary.info !== 1 ? "s" : ""}
                  </Text>
                </HStack>
              )}
            </HStack>
          </VStack>
          <Button size="sm" variant="ghost" onClick={onClose}>
            Close
          </Button>
        </HStack>
      </Box>

      {/* Issues List */}
      <Box maxH="400px" overflow="auto">
        <VStack align="stretch" spacing={0}>
          {issues.map((issue, index) => (
            <Box key={index}>
              <Box
                p={4}
                _hover={{ bg: "gray.50" }}
                cursor={
                  issue.itemId && onNavigateToItem ? "pointer" : "default"
                }
                onClick={() => handleNavigateToItem(issue)}
              >
                <VStack align="stretch" spacing={2}>
                  <HStack spacing={3} align="start">
                    {getIssueIcon(issue.type)}
                    <VStack align="start" spacing={1} flex="1">
                      <HStack spacing={2} align="center">
                        <Text
                          fontWeight="medium"
                          color={`${getIssueColor(issue.type)}.800`}
                        >
                          {issue.message}
                        </Text>
                        {issue.itemId && issue.itemType && (
                          <HStack spacing={1}>
                            {getItemIcon(issue.itemType)}
                            <Badge
                              size="sm"
                              colorPalette={getIssueColor(issue.type)}
                              variant="subtle"
                            >
                              {issue.itemId}
                            </Badge>
                          </HStack>
                        )}
                      </HStack>
                      {issue.suggestion && (
                        <Text fontSize="sm" color="gray.600">
                          💡 {issue.suggestion}
                        </Text>
                      )}
                    </VStack>
                  </HStack>
                </VStack>
              </Box>
              {index < issues.length - 1 && <Separator />}
            </Box>
          ))}
        </VStack>
      </Box>

      {/* Footer with overall status */}
      {!isValid && (
        <Box p={3} bg="red.50" borderTopWidth="1px">
          <Alert.Root status="error" size="sm">
            <Alert.Indicator />
            <Alert.Content>
              <Alert.Description>
                This ontology has validation issues that should be addressed
                before export or publication.
              </Alert.Description>
            </Alert.Content>
          </Alert.Root>
        </Box>
      )}
    </Box>
  );
};
