import React, { useState } from "react";
import {
  Box,
  VStack,
  HStack,
  Text,
  Button,
  Input,
  IconButton,
} from "@chakra-ui/react";
import { Plus, ChevronRight, ChevronDown, Hash, Trash2 } from "lucide-react";
import { OWLClass } from "@trustgraph/react-state";
import { useNotification } from "@trustgraph/react-state";

interface ClassTreeProps {
  classes: Record<string, OWLClass>;
  selectedClassId?: string | null;
  onSelectClass: (classId: string) => void;
  onCreateClass: (className: string) => void;
  onUpdateClass: (classId: string, updatedClass: OWLClass) => void;
  onDeleteClass: (classId: string) => void;
}

export const ClassTree: React.FC<ClassTreeProps> = ({
  classes,
  selectedClassId,
  onSelectClass,
  onCreateClass,
  onUpdateClass,
  onDeleteClass,
}) => {
  const [isCreating, setIsCreating] = useState(false);
  const [newClassName, setNewClassName] = useState("");
  const [expandedClasses, setExpandedClasses] = useState<Set<string>>(
    new Set(),
  );
  const [draggedClassId, setDraggedClassId] = useState<string | null>(null);
  const [dragOverClassId, setDragOverClassId] = useState<string | null>(null);
  const notify = useNotification();

  const classEntries = Object.entries(classes);

  // Build class hierarchy
  const buildClassHierarchy = () => {
    const roots: string[] = [];
    const children: Record<string, string[]> = {};

    // Find root classes (no subClassOf) and build children map
    classEntries.forEach(([classId, owlClass]) => {
      const parent = owlClass["rdfs:subClassOf"];
      if (!parent || parent.trim() === "") {
        roots.push(classId);
      } else {
        if (!children[parent]) {
          children[parent] = [];
        }
        children[parent].push(classId);
      }
    });

    return { roots, children };
  };

  const { roots, children } = buildClassHierarchy();

  const handleCreateClass = () => {
    if (newClassName.trim()) {
      onCreateClass(newClassName.trim());
      setNewClassName("");
      setIsCreating(false);
    }
  };

  const handleCancelCreate = () => {
    setNewClassName("");
    setIsCreating(false);
  };

  const toggleExpanded = (classId: string) => {
    const newExpanded = new Set(expandedClasses);
    if (newExpanded.has(classId)) {
      newExpanded.delete(classId);
    } else {
      newExpanded.add(classId);
    }
    setExpandedClasses(newExpanded);
  };

  const getClassLabel = (owlClass: OWLClass): string => {
    if (owlClass["rdfs:label"] && owlClass["rdfs:label"].length > 0) {
      return owlClass["rdfs:label"][0].value;
    }
    // Fallback to extracting from URI
    const parts = owlClass.uri.split(/[/#]/);
    return parts[parts.length - 1] || "Unnamed Class";
  };

  // Drag and drop handlers
  const handleDragStart = (e: React.DragEvent, classId: string) => {
    setDraggedClassId(classId);
    e.dataTransfer.setData("text/plain", classId);
    e.dataTransfer.effectAllowed = "move";
  };

  const handleDragOver = (e: React.DragEvent, targetClassId: string) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    setDragOverClassId(targetClassId);
  };

  const handleDragLeave = () => {
    setDragOverClassId(null);
  };

  const handleDrop = (e: React.DragEvent, targetClassId: string) => {
    e.preventDefault();
    setDragOverClassId(null);

    const sourceClassId = e.dataTransfer.getData("text/plain");

    if (sourceClassId && sourceClassId !== targetClassId && draggedClassId) {
      // Check for circular dependency
      if (isCircularDependency(sourceClassId, targetClassId)) {
        notify.warning(
          "Cannot create circular dependency: this would make a class a subclass of itself.",
        );
        setDraggedClassId(null);
        return;
      }

      // Update the dragged class to have the target as its parent
      const sourceClass = classes[sourceClassId];
      if (sourceClass) {
        const updatedClass: OWLClass = {
          ...sourceClass,
          "rdfs:subClassOf": targetClassId,
        };
        onUpdateClass(sourceClassId, updatedClass);
      }
    }

    setDraggedClassId(null);
  };

  const handleDropToRoot = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOverClassId(null);

    const sourceClassId = e.dataTransfer.getData("text/plain");

    if (sourceClassId && draggedClassId) {
      // Make the class a root class (no parent)
      const sourceClass = classes[sourceClassId];
      if (sourceClass) {
        const updatedClass: OWLClass = {
          ...sourceClass,
          "rdfs:subClassOf": undefined,
        };
        onUpdateClass(sourceClassId, updatedClass);
      }
    }

    setDraggedClassId(null);
  };

  // Check if making sourceClassId a child of targetClassId would create a circular dependency
  const isCircularDependency = (
    sourceClassId: string,
    targetClassId: string,
  ): boolean => {
    const visited = new Set<string>();

    const checkPath = (currentId: string): boolean => {
      if (currentId === sourceClassId) return true;
      if (visited.has(currentId)) return false;

      visited.add(currentId);
      const currentClass = classes[currentId];
      const parentId = currentClass?.["rdfs:subClassOf"];

      if (parentId && parentId.trim()) {
        return checkPath(parentId);
      }

      return false;
    };

    return checkPath(targetClassId);
  };

  // Recursive component to render class hierarchy
  const renderClassNode = (
    classId: string,
    depth: number = 0,
  ): React.ReactNode => {
    const owlClass = classes[classId];
    if (!owlClass) return null;

    const isSelected = classId === selectedClassId;
    const isExpanded = expandedClasses.has(classId);
    const hasSubclasses = children[classId] && children[classId].length > 0;
    const isDraggedOver = dragOverClassId === classId;
    const isDragging = draggedClassId === classId;

    return (
      <Box key={classId}>
        <HStack
          role="group"
          p={3}
          pl={3 + depth * 20} // Indent based on depth
          spacing={3}
          bg={
            isDraggedOver
              ? "green.100"
              : isSelected
                ? "blue.50"
                : isDragging
                  ? "gray.200"
                  : "transparent"
          }
          borderWidth={isDraggedOver ? "2px" : "0"}
          borderColor="green.400"
          borderStyle="dashed"
          cursor={isDragging ? "grabbing" : "grab"}
          opacity={isDragging ? 0.5 : 1}
          _hover={{
            bg: isDraggedOver
              ? "green.100"
              : isSelected
                ? "blue.100"
                : "gray.50",
          }}
          onClick={() => onSelectClass(classId)}
          draggable
          onDragStart={(e) => handleDragStart(e, classId)}
          onDragOver={(e) => handleDragOver(e, classId)}
          onDragLeave={handleDragLeave}
          onDrop={(e) => handleDrop(e, classId)}
        >
          {hasSubclasses ? (
            <IconButton
              size="xs"
              variant="ghost"
              onClick={(e) => {
                e.stopPropagation();
                toggleExpanded(classId);
              }}
            >
              {isExpanded ? (
                <ChevronDown size={12} />
              ) : (
                <ChevronRight size={12} />
              )}
            </IconButton>
          ) : (
            <Box w={6} /> // Spacer for alignment
          )}

          <Hash size={14} color="#666" />

          <VStack align="start" spacing={0} flex="1" minW="0">
            <Text
              fontSize="sm"
              fontWeight={isSelected ? "semibold" : "normal"}
              color={isSelected ? "blue.800" : "gray.800"}
              noOfLines={1}
            >
              {getClassLabel(owlClass)}
            </Text>
            {owlClass["rdfs:comment"] && (
              <Text fontSize="xs" color="gray.500" noOfLines={1}>
                {owlClass["rdfs:comment"]}
              </Text>
            )}
          </VStack>

          {/* Delete button - only show on hover and not while dragging */}
          {!isDragging && (
            <IconButton
              size="xs"
              variant="ghost"
              colorPalette="red"
              onClick={(e) => {
                e.stopPropagation();
                onDeleteClass(classId);
              }}
              opacity={0}
              _groupHover={{ opacity: 1 }}
              transition="opacity 0.2s"
              aria-label={`Delete ${getClassLabel(owlClass)}`}
            >
              <Trash2 size={12} />
            </IconButton>
          )}
        </HStack>

        {/* Render subclasses when expanded */}
        {hasSubclasses && isExpanded && (
          <Box>
            {children[classId].map((childId) =>
              renderClassNode(childId, depth + 1),
            )}
          </Box>
        )}
      </Box>
    );
  };

  return (
    <VStack align="stretch" spacing={0} h="100%">
      {/* Header */}
      <Box p={4} borderBottomWidth="1px" bg="gray.50">
        <HStack justify="space-between">
          <Text fontWeight="semibold" fontSize="md" color="gray.800">
            Classes ({classEntries.length})
          </Text>
          <IconButton
            size="xs"
            variant="ghost"
            onClick={() => setIsCreating(true)}
            disabled={isCreating}
          >
            <Plus size={14} />
          </IconButton>
        </HStack>
      </Box>

      {/* Class List */}
      <Box
        flex="1"
        overflow="auto"
        onDragOver={(e) => {
          e.preventDefault();
          e.dataTransfer.dropEffect = "move";
        }}
        onDrop={handleDropToRoot}
      >
        <VStack align="stretch" spacing={0}>
          {/* New Class Creation */}
          {isCreating && (
            <Box p={3} bg="blue.25" borderBottomWidth="1px">
              <VStack spacing={2}>
                <Input
                  size="sm"
                  placeholder="Class name (e.g., Document)"
                  value={newClassName}
                  onChange={(e) => setNewClassName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleCreateClass();
                    if (e.key === "Escape") handleCancelCreate();
                  }}
                  autoFocus
                />
                <HStack spacing={2}>
                  <Button
                    size="xs"
                    colorPalette="blue"
                    onClick={handleCreateClass}
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
            </Box>
          )}

          {/* Drop zone indicator when dragging */}
          {draggedClassId && (
            <Box
              p={3}
              mx={2}
              mb={2}
              borderWidth="2px"
              borderStyle="dashed"
              borderColor="green.400"
              bg="green.50"
              borderRadius="md"
              textAlign="center"
            >
              <Text fontSize="xs" color="green.600" fontWeight="medium">
                Drop here to make "
                {classes[draggedClassId] &&
                  getClassLabel(classes[draggedClassId])}
                " a top-level class
              </Text>
            </Box>
          )}

          {/* Existing Classes */}
          {classEntries.length === 0 && !isCreating ? (
            <Box p={4} textAlign="center">
              <Text color="gray.500" fontSize="sm">
                No classes yet
              </Text>
              <Button
                size="sm"
                variant="ghost"
                colorPalette="blue"
                mt={2}
                onClick={() => setIsCreating(true)}
              >
                <Plus size={14} style={{ marginRight: "4px" }} />
                Add First Class
              </Button>
            </Box>
          ) : (
            // Render hierarchy starting from root classes
            roots.map((rootId) => renderClassNode(rootId))
          )}
        </VStack>
      </Box>
    </VStack>
  );
};
