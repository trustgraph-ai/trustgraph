import React, { useState } from "react";
import {
  Box,
  VStack,
  HStack,
  Text,
  Button,
  Input,
  Heading,
  Card,
} from "@chakra-ui/react";
import { Plus, Sparkles, FileText, X } from "lucide-react";

interface WelcomePanelProps {
  ontologyName: string;
  onCreateClass: (className: string) => void;
  onDismiss: () => void;
}

export const WelcomePanel: React.FC<WelcomePanelProps> = ({
  ontologyName,
  onCreateClass,
  onDismiss,
}) => {
  const [isCreating, setIsCreating] = useState(false);
  const [newClassName, setNewClassName] = useState("");

  const handleCreateClass = () => {
    if (newClassName.trim()) {
      onCreateClass(newClassName.trim());
      setNewClassName("");
      setIsCreating(false);
    }
  };

  const handleQuickCreate = (className: string) => {
    onCreateClass(className);
  };

  return (
    <Card.Root maxW="600px" w="full">
      <Card.Header>
        <HStack justify="space-between" align="start">
          <VStack align="start" spacing={1}>
            <Heading size="lg">Welcome to {ontologyName}!</Heading>
            <Text color="gray.600">
              Your ontology is ready. Here's what to do next:
            </Text>
          </VStack>
          <Button size="sm" variant="ghost" onClick={onDismiss}>
            <X size={16} />
          </Button>
        </HStack>
      </Card.Header>

      <Card.Body>
        <VStack spacing={6} align="stretch">
          {/* Quick Start Options */}
          <VStack spacing={3} align="stretch">
            <Text fontSize="md" fontWeight="semibold">
              Quick Start
            </Text>

            {!isCreating ? (
              <VStack spacing={2}>
                <Button
                  size="lg"
                  colorPalette="blue"
                  leftIcon={<Plus size={20} />}
                  onClick={() => setIsCreating(true)}
                  w="full"
                >
                  Add First Class
                </Button>

                <Text fontSize="sm" color="gray.500" textAlign="center">
                  Start by defining the main object types in your domain
                </Text>
              </VStack>
            ) : (
              <VStack spacing={3} p={4} bg="blue.50" borderRadius="md">
                <Text fontSize="sm" fontWeight="medium">
                  What's your first class?
                </Text>
                <Input
                  placeholder="Class name (e.g., Document, Person, Product)"
                  value={newClassName}
                  onChange={(e) => setNewClassName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleCreateClass();
                    if (e.key === "Escape") setIsCreating(false);
                  }}
                  autoFocus
                />
                <HStack spacing={2}>
                  <Button
                    size="sm"
                    colorPalette="blue"
                    onClick={handleCreateClass}
                  >
                    Create Class
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setIsCreating(false)}
                  >
                    Cancel
                  </Button>
                </HStack>
              </VStack>
            )}
          </VStack>

          {/* Quick Examples */}
          {!isCreating && (
            <VStack spacing={3} align="stretch">
              <Text fontSize="md" fontWeight="semibold">
                Common Starting Points
              </Text>

              <Text fontSize="sm" color="gray.600">
                Or choose from these common class types:
              </Text>

              <HStack spacing={2} flexWrap="wrap">
                {[
                  "Document",
                  "Person",
                  "Organization",
                  "Product",
                  "Event",
                ].map((className) => (
                  <Button
                    key={className}
                    size="sm"
                    variant="outline"
                    onClick={() => handleQuickCreate(className)}
                  >
                    {className}
                  </Button>
                ))}
              </HStack>
            </VStack>
          )}

          {/* Future Features Preview */}
          <VStack spacing={3} align="stretch">
            <Text fontSize="md" fontWeight="semibold">
              Coming Soon
            </Text>

            <VStack spacing={2}>
              <HStack
                p={3}
                bg="gray.50"
                borderRadius="md"
                spacing={3}
                opacity={0.6}
                w="full"
                justify="start"
              >
                <Sparkles size={18} />
                <VStack align="start" spacing={0}>
                  <Text fontSize="sm" fontWeight="medium">
                    AI Assistant (Phase 7)
                  </Text>
                  <Text fontSize="xs" color="gray.500">
                    Let AI suggest classes and properties for your domain
                  </Text>
                </VStack>
              </HStack>

              <HStack
                p={3}
                bg="gray.50"
                borderRadius="md"
                spacing={3}
                opacity={0.6}
                w="full"
                justify="start"
              >
                <FileText size={18} />
                <VStack align="start" spacing={0}>
                  <Text fontSize="sm" fontWeight="medium">
                    Import Ontology (Phase 6)
                  </Text>
                  <Text fontSize="xs" color="gray.500">
                    Load existing OWL, RDF, or Turtle files
                  </Text>
                </VStack>
              </HStack>
            </VStack>
          </VStack>

          {/* Dismiss Option */}
          <Box pt={4} borderTopWidth="1px">
            <HStack justify="space-between">
              <Text fontSize="sm" color="gray.500">
                Ready to start building your ontology?
              </Text>
              <Button size="sm" variant="ghost" onClick={onDismiss}>
                Skip Welcome
              </Button>
            </HStack>
          </Box>
        </VStack>
      </Card.Body>
    </Card.Root>
  );
};
