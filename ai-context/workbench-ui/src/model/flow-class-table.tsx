import { createColumnHelper } from "@tanstack/react-table";
import { Checkbox, Badge, HStack, Text } from "@chakra-ui/react";
import { FlowClassDefinition } from "@trustgraph/react-state";

/**
 * Flow class data structure for the flow class table
 * Represents a single flow class with its metadata and properties
 */
export type FlowClassRow = FlowClassDefinition;

// Create a column helper instance for type-safe column definitions
export const columnHelper = createColumnHelper<FlowClassRow>();

/**
 * Helper function to determine the selection state of the table header
 * checkbox
 * Returns the appropriate state for the "select all" checkbox
 * @param {Object} table - React Table instance
 * @returns {boolean|string} - true if all selected, "indeterminate" if some
 * selected, false if none
 */
const selectionState = (table) => {
  if (table.getIsAllRowsSelected()) return true;
  if (table.getIsSomeRowsSelected()) return "indeterminate";
  return false;
};

/**
 * Column definitions for the flow class table
 * Defines how each column should be rendered and what data it displays
 */
export const flowClassColumns = [
  // Selection column - provides row selection functionality with checkboxes
  columnHelper.display({
    id: "select",
    header: ({ table }) => (
      // Header checkbox for selecting/deselecting all rows
      <Checkbox.Root
        size="sm"
        variant="solid"
        checked={selectionState(table)}
        onChange={table.getToggleAllRowsSelectedHandler()}
      >
        <Checkbox.HiddenInput />
        <Checkbox.Control />
      </Checkbox.Root>
    ),
    cell: ({ row }) => (
      // Individual row checkbox for selecting/deselecting single rows
      <Checkbox.Root
        size="sm"
        variant="solid"
        checked={row.getIsSelected()}
        onChange={row.getToggleSelectedHandler()}
      >
        <Checkbox.HiddenInput />
        <Checkbox.Control />
      </Checkbox.Root>
    ),
  }),

  // ID column - displays the flow class ID
  columnHelper.display({
    id: "id",
    header: "ID",
    cell: ({ row }) => {
      const flowClass = row.original;
      return (
        <Text fontFamily="mono" fontSize="sm">
          {flowClass.id || "No ID"}
        </Text>
      );
    },
  }),

  // Description column - displays flow class description
  columnHelper.display({
    id: "description",
    header: "Description",
    cell: ({ row }) => {
      const flowClass = row.original;
      const description = flowClass.description;
      return (
        <Text fontSize="sm" noOfLines={2}>
          {description || "No description"}
        </Text>
      );
    },
  }),

  // Processors column - shows count of class and flow processors
  columnHelper.display({
    id: "processors",
    header: "Processors",
    cell: ({ row }) => {
      const flowClass = row.original;
      const classCount = Object.keys(flowClass.class || {}).length;
      const flowCount = Object.keys(flowClass.flow || {}).length;

      return (
        <HStack gap={2}>
          <Badge colorPalette="blue" size="sm">
            {classCount} class
          </Badge>
          <Badge colorPalette="green" size="sm">
            {flowCount} flow
          </Badge>
        </HStack>
      );
    },
  }),

  // Interfaces column - shows count of interfaces
  columnHelper.display({
    id: "interfaces",
    header: "Interfaces",
    cell: ({ row }) => {
      const flowClass = row.original;
      const interfaceCount = Object.keys(flowClass.interfaces || {}).length;

      return (
        <Badge colorPalette="purple" size="sm">
          {interfaceCount} interfaces
        </Badge>
      );
    },
  }),

  // Tags column - displays flow class tags
  columnHelper.display({
    id: "tags",
    header: "Tags",
    cell: ({ row }) => {
      const flowClass = row.original;
      const tags = flowClass.tags || [];
      if (tags.length === 0) {
        return (
          <Text fontSize="xs" color="fg.muted">
            No tags
          </Text>
        );
      }

      return (
        <HStack gap={1} flexWrap="wrap">
          {tags.slice(0, 3).map((tag, index) => (
            <Badge key={index} colorPalette="gray" size="xs" variant="outline">
              {tag}
            </Badge>
          ))}
          {tags.length > 3 && (
            <Text fontSize="xs" color="fg.muted">
              +{tags.length - 3} more
            </Text>
          )}
        </HStack>
      );
    },
  }),
];
