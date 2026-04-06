import { createColumnHelper } from "@tanstack/react-table";
import { Tag, Checkbox } from "@chakra-ui/react";
import { CollectionMetadata } from "@trustgraph/react-state";

// Create a column helper instance for type-safe column definitions
export const columnHelper = createColumnHelper<CollectionMetadata>();

/**
 * Helper function to determine the selection state of the table header checkbox
 * Returns the appropriate state for the "select all" checkbox
 * @param {Object} table - React Table instance
 * @returns {boolean|string} - true if all selected, "indeterminate" if some selected, false if none
 */
const selectionState = (table) => {
  if (table.getIsAllRowsSelected()) return true;
  if (table.getIsSomeRowsSelected()) return "indeterminate";
  return false;
};

/**
 * Column definitions for the collection table
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

  // Collection ID column - displays the unique collection identifier
  columnHelper.accessor("collection", {
    header: "Collection ID",
    cell: (info) => info.getValue(),
  }),

  // Name column - displays the display name of the collection
  columnHelper.accessor("name", {
    header: "Name",
    cell: (info) => info.getValue(),
  }),

  // Description column - displays collection description
  columnHelper.accessor("description", {
    header: "Description",
    cell: (info) => info.getValue(),
  }),

  // Tags column - displays collection tags as visual tag components
  columnHelper.accessor("tags", {
    header: "Tags",
    cell: (info) =>
      // Render each tag as a Chakra UI Tag component with margin spacing
      info.getValue()?.map((tag) => (
        <Tag.Root key={tag} mr={2} size="sm">
          <Tag.Label>{tag}</Tag.Label>
        </Tag.Root>
      )),
  }),

  // Created timestamp column
  columnHelper.accessor("created_at", {
    header: "Created",
    cell: (info) => {
      const date = new Date(info.getValue());
      return date.toLocaleString();
    },
  }),

  // Updated timestamp column
  columnHelper.accessor("updated_at", {
    header: "Updated",
    cell: (info) => {
      const date = new Date(info.getValue());
      return date.toLocaleString();
    },
  }),
];
