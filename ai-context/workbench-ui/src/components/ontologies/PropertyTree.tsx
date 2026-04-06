import React, { useState } from "react";
import {
  Box,
  VStack,
  HStack,
  Text,
  Button,
  Input,
  IconButton,
  Tabs,
} from "@chakra-ui/react";
import { Plus, Link, Type, Trash2 } from "lucide-react";
import {
  OWLObjectProperty,
  OWLDatatypeProperty,
} from "@trustgraph/react-state";

interface PropertyTreeProps {
  objectProperties: Record<string, OWLObjectProperty>;
  datatypeProperties: Record<string, OWLDatatypeProperty>;
  selectedPropertyId?: string | null;
  selectedPropertyType?: "object" | "datatype" | null;
  onSelectProperty: (propertyId: string, type: "object" | "datatype") => void;
  onCreateObjectProperty: (propertyName: string) => void;
  onCreateDatatypeProperty: (propertyName: string) => void;
  onDeleteProperty: (propertyId: string, type: "object" | "datatype") => void;
}

export const PropertyTree: React.FC<PropertyTreeProps> = ({
  objectProperties,
  datatypeProperties,
  selectedPropertyId,
  selectedPropertyType,
  onSelectProperty,
  onCreateObjectProperty,
  onCreateDatatypeProperty,
  onDeleteProperty,
}) => {
  const [isCreating, setIsCreating] = useState<"object" | "datatype" | null>(
    null,
  );
  const [newPropertyName, setNewPropertyName] = useState("");

  const objectPropertyEntries = Object.entries(objectProperties);
  const datatypePropertyEntries = Object.entries(datatypeProperties);

  const handleCreateProperty = () => {
    if (newPropertyName.trim() && isCreating) {
      if (isCreating === "object") {
        onCreateObjectProperty(newPropertyName.trim());
      } else {
        onCreateDatatypeProperty(newPropertyName.trim());
      }
      setNewPropertyName("");
      setIsCreating(null);
    }
  };

  const handleCancelCreate = () => {
    setNewPropertyName("");
    setIsCreating(null);
  };

  const getPropertyLabel = (
    property: OWLObjectProperty | OWLDatatypeProperty,
  ): string => {
    if (property["rdfs:label"] && property["rdfs:label"].length > 0) {
      return property["rdfs:label"][0].value;
    }
    // Fallback to extracting from URI
    const parts = property.uri.split(/[/#]/);
    return parts[parts.length - 1] || "Unnamed Property";
  };

  const renderPropertyList = (
    entries: [string, OWLObjectProperty | OWLDatatypeProperty][],
    type: "object" | "datatype",
    icon: React.ReactNode,
    emptyMessage: string,
  ) => (
    <VStack align="stretch" spacing={0}>
      {entries.length === 0 ? (
        <Box p={3} textAlign="center">
          <Text color="gray.500" fontSize="xs">
            {emptyMessage}
          </Text>
        </Box>
      ) : (
        entries.map(([propertyId, property]) => {
          const isSelected =
            propertyId === selectedPropertyId && type === selectedPropertyType;
          return (
            <HStack
              key={propertyId}
              role="group"
              p={3}
              spacing={3}
              bg={isSelected ? "blue.50" : "transparent"}
              cursor="pointer"
              _hover={{ bg: isSelected ? "blue.100" : "gray.50" }}
              onClick={() => onSelectProperty(propertyId, type)}
            >
              {icon}
              <VStack align="start" spacing={0} flex="1" minW="0">
                <Text
                  fontSize="sm"
                  fontWeight={isSelected ? "semibold" : "normal"}
                  color={isSelected ? "blue.800" : "gray.800"}
                  noOfLines={1}
                >
                  {getPropertyLabel(property)}
                </Text>
                {property["rdfs:comment"] && (
                  <Text fontSize="xs" color="gray.500" noOfLines={1}>
                    {property["rdfs:comment"]}
                  </Text>
                )}
              </VStack>

              {/* Delete button - show on hover */}
              <IconButton
                size="xs"
                variant="ghost"
                colorPalette="red"
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteProperty(propertyId, type);
                }}
                opacity={0}
                _groupHover={{ opacity: 1 }}
                transition="opacity 0.2s"
                aria-label={`Delete ${getPropertyLabel(property)}`}
              >
                <Trash2 size={12} />
              </IconButton>
            </HStack>
          );
        })
      )}
    </VStack>
  );

  return (
    <VStack align="stretch" spacing={0} h="100%">
      {/* Header */}
      <Box p={4} borderBottomWidth="1px" bg="gray.50">
        <HStack justify="space-between">
          <Text fontWeight="semibold" fontSize="md" color="gray.800">
            Properties (
            {objectPropertyEntries.length + datatypePropertyEntries.length})
          </Text>
        </HStack>
      </Box>

      {/* Property Tabs */}
      <Box flex="1" overflow="auto">
        <Tabs.Root defaultValue="object">
          <Tabs.List>
            <Tabs.Trigger value="object">
              <Link size={14} style={{ marginRight: "4px" }} />
              Object ({objectPropertyEntries.length})
            </Tabs.Trigger>
            <Tabs.Trigger value="datatype">
              <Type size={14} style={{ marginRight: "4px" }} />
              Datatype ({datatypePropertyEntries.length})
            </Tabs.Trigger>
          </Tabs.List>

          <Tabs.Content value="object">
            <VStack align="stretch" spacing={0}>
              {/* Create Object Property */}
              <Box p={3} borderBottomWidth="1px" bg="gray.25">
                {isCreating === "object" ? (
                  <VStack spacing={2}>
                    <Input
                      size="sm"
                      placeholder="Property name (e.g., hasAuthor)"
                      value={newPropertyName}
                      onChange={(e) => setNewPropertyName(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") handleCreateProperty();
                        if (e.key === "Escape") handleCancelCreate();
                      }}
                      autoFocus
                    />
                    <HStack spacing={2}>
                      <Button
                        size="xs"
                        colorPalette="blue"
                        onClick={handleCreateProperty}
                      >
                        Create
                      </Button>
                      <Button
                        size="xs"
                        variant="ghost"
                        onClick={handleCancelCreate}
                      >
                        Cancel
                      </Button>
                    </HStack>
                  </VStack>
                ) : (
                  <Button
                    size="sm"
                    variant="ghost"
                    colorPalette="blue"
                    onClick={() => setIsCreating("object")}
                    w="100%"
                  >
                    <Plus size={14} style={{ marginRight: "4px" }} />
                    Add Object Property
                  </Button>
                )}
              </Box>

              {/* Object Properties List */}
              {renderPropertyList(
                objectPropertyEntries,
                "object",
                <Link size={14} color="#666" />,
                "No object properties",
              )}
            </VStack>
          </Tabs.Content>

          <Tabs.Content value="datatype">
            <VStack align="stretch" spacing={0}>
              {/* Create Datatype Property */}
              <Box p={3} borderBottomWidth="1px" bg="gray.25">
                {isCreating === "datatype" ? (
                  <VStack spacing={2}>
                    <Input
                      size="sm"
                      placeholder="Property name (e.g., hasTitle)"
                      value={newPropertyName}
                      onChange={(e) => setNewPropertyName(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") handleCreateProperty();
                        if (e.key === "Escape") handleCancelCreate();
                      }}
                      autoFocus
                    />
                    <HStack spacing={2}>
                      <Button
                        size="xs"
                        colorPalette="blue"
                        onClick={handleCreateProperty}
                      >
                        Create
                      </Button>
                      <Button
                        size="xs"
                        variant="ghost"
                        onClick={handleCancelCreate}
                      >
                        Cancel
                      </Button>
                    </HStack>
                  </VStack>
                ) : (
                  <Button
                    size="sm"
                    variant="ghost"
                    colorPalette="blue"
                    onClick={() => setIsCreating("datatype")}
                    w="100%"
                  >
                    <Plus size={14} style={{ marginRight: "4px" }} />
                    Add Datatype Property
                  </Button>
                )}
              </Box>

              {/* Datatype Properties List */}
              {renderPropertyList(
                datatypePropertyEntries,
                "datatype",
                <Type size={14} color="#666" />,
                "No datatype properties",
              )}
            </VStack>
          </Tabs.Content>
        </Tabs.Root>
      </Box>
    </VStack>
  );
};
