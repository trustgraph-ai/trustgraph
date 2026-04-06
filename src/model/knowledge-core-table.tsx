import { createColumnHelper } from "@tanstack/react-table";
import { Checkbox } from "@chakra-ui/react";

/**
 * Knowledge core data structure for the knowledge core table
 * Represents a single knowledge core with its metadata and properties
 */
export type KnowledgeCore = {
  id: string; // Unique identifier for the knowledge core
};

// Create a column helper instance for type-safe column definitions
export const columnHelper = createColumnHelper<KnowledgeCore>();

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
 * Column definitions for the flow table
 * Defines how each column should be rendered and what data it displays
 */
export const columns = [
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

  // ID column - displays the flow ID
  columnHelper.accessor("id", {
    header: "ID",
    cell: (info) => info.getValue(),
  }),
];
