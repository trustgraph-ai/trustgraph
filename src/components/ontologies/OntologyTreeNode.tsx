import React, { useMemo } from "react";
import {
  Box,
  VStack,
  HStack,
  Text,
  IconButton,
  Menu,
  useDisclosure,
  Badge,
} from "@chakra-ui/react";
import {
  ChevronRight,
  ChevronDown,
  MoreVertical,
  Plus,
  Edit,
  Trash2,
  Move,
} from "lucide-react";
import { OntologyConcept, Ontology } from "@trustgraph/react-state";

interface OntologyTreeNodeProps {
  concept: OntologyConcept;
  ontology: Ontology;
  level: number;
  isSelected: boolean;
  searchTerm: string;
  selectedConceptId?: string;
  onSelect: (conceptId: string) => void;
  onAdd: (parentId: string) => void;
  onEdit: (conceptId: string) => void;
  onDelete: (conceptId: string) => void;
  onMove: (conceptId: string) => void;
}

export const OntologyTreeNode: React.FC<OntologyTreeNodeProps> = ({
  concept,
  ontology,
  level,
  isSelected,
  searchTerm,
  selectedConceptId,
  onSelect,
  onAdd,
  onEdit,
  onDelete,
  onMove,
}) => {
  const { isOpen, onToggle } = useDisclosure({ defaultIsOpen: level < 2 });

  const children = useMemo(() => concept.narrower || [], [concept.narrower]);
  const hasChildren = children.length > 0;

  // Filter children based on search term
  const filteredChildren = useMemo(() => {
    if (!searchTerm) return children;
    return children.filter((childId) => {
      const childConcept = ontology.concepts[childId];
      return (
        childConcept?.prefLabel
          .toLowerCase()
          .includes(searchTerm.toLowerCase()) ||
        childConcept?.definition
          ?.toLowerCase()
          .includes(searchTerm.toLowerCase())
      );
    });
  }, [children, searchTerm, ontology.concepts]);

  const shouldShowNode =
    !searchTerm ||
    concept.prefLabel.toLowerCase().includes(searchTerm.toLowerCase()) ||
    concept.definition?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    filteredChildren.length > 0;

  if (!shouldShowNode) return null;

  const paddingLeft = level * 20;

  return (
    <VStack gap={1} align="stretch">
      <HStack
        gap={2}
        p={2}
        borderRadius="md"
        bg={isSelected ? "primary.muted" : "transparent"}
        borderLeft={isSelected ? "3px solid" : "3px solid transparent"}
        borderLeftColor={isSelected ? "primary.solid" : "transparent"}
        _hover={{ bg: "bg.muted" }}
        cursor="pointer"
        paddingLeft={paddingLeft}
      >
        {/* Expand/collapse button */}
        <IconButton
          aria-label="Toggle"
          size="xs"
          variant="ghost"
          onClick={hasChildren ? onToggle : undefined}
          visibility={hasChildren ? "visible" : "hidden"}
        >
          {hasChildren ? isOpen ? <ChevronDown /> : <ChevronRight /> : null}
        </IconButton>

        {/* Concept content */}
        <Box flex="1" onClick={() => onSelect(concept.id)}>
          <HStack justify="space-between" align="center">
            <VStack align="start" gap={0} flex="1">
              <HStack>
                <Text
                  fontWeight={concept.topConcept ? "bold" : "medium"}
                  fontSize="sm"
                >
                  {concept.prefLabel}
                </Text>
                {concept.topConcept && (
                  <Badge size="xs" colorPalette="primary">
                    Top
                  </Badge>
                )}
                {concept.notation && (
                  <Badge size="xs" variant="outline">
                    {concept.notation}
                  </Badge>
                )}
              </HStack>
              {concept.definition && (
                <Text fontSize="xs" color="fg.muted" noOfLines={1}>
                  {concept.definition}
                </Text>
              )}
            </VStack>

            {/* Context menu */}
            <Menu.Root>
              <Menu.Trigger asChild>
                <IconButton
                  aria-label="Options"
                  variant="ghost"
                  size="xs"
                  onClick={(e) => e.stopPropagation()}
                >
                  <MoreVertical />
                </IconButton>
              </Menu.Trigger>
              <Menu.Content>
                <Menu.Item onClick={() => onAdd(concept.id)}>
                  <Plus /> Add Child Concept
                </Menu.Item>
                <Menu.Item onClick={() => onEdit(concept.id)}>
                  <Edit /> Edit Concept
                </Menu.Item>
                <Menu.Item onClick={() => onMove(concept.id)}>
                  <Move /> Move Concept
                </Menu.Item>
                <Menu.Item onClick={() => onDelete(concept.id)} color="red.fg">
                  <Trash2 /> Delete Concept
                </Menu.Item>
              </Menu.Content>
            </Menu.Root>
          </HStack>
        </Box>
      </HStack>

      {/* Children */}
      {hasChildren && isOpen && (
        <VStack gap={1} align="stretch">
          {filteredChildren.map((childId) => {
            const childConcept = ontology.concepts[childId];
            if (!childConcept) return null;

            return (
              <OntologyTreeNode
                key={childId}
                concept={childConcept}
                ontology={ontology}
                level={level + 1}
                isSelected={selectedConceptId === childId}
                searchTerm={searchTerm}
                selectedConceptId={selectedConceptId}
                onSelect={onSelect}
                onAdd={onAdd}
                onEdit={onEdit}
                onDelete={onDelete}
                onMove={onMove}
              />
            );
          })}
        </VStack>
      )}
    </VStack>
  );
};
