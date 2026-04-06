import { createColumnHelper } from "@tanstack/react-table";
import { Tag, Checkbox } from "@chakra-ui/react";
import { timeString } from "../utils/time-string.ts";

/**
 * Document data structure for the document table
 * Represents a single document with its metadata and properties
 */
export type Document = {
  id: string; // Unique identifier for the document
  title: string; // Display title of the document
  time: number; // Timestamp (likely Unix timestamp)
  kind: string; // Document type/category
  user: string; // User who created/owns the document
  comments: string; // Description or comments about the document
  tags: string[]; // Array of tags associated with the document
  metadata: {
    // Structured metadata, subject-predicate-object form
    s: { v: string; e: boolean }; // Subject with value and enabled flag
    p: { v: string; e: boolean }; // Predicate with value and enabled flag
    o: { v: string; e: boolean }; // Object with value and enabled flag
  }[];
};

// Create a column helper instance for type-safe column definitions
export const columnHelper = createColumnHelper<Document>();

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
 * Column definitions for the document table
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

  // Title column - displays the document title
  columnHelper.accessor("title", {
    header: "Title",
    cell: (info) => info.getValue(),
  }),

  // Time column - displays formatted timestamp
  columnHelper.accessor("time", {
    header: "Time",
    cell: (info) => timeString(info.getValue()), // Convert to readable string
  }),

  // Description column - displays document comments/description
  // Note: Maps to 'comments' field but displays as 'Description' for better
  // UX
  columnHelper.accessor("comments", {
    id: "description",
    header: "Description",
    cell: (info) => info.getValue(),
  }),

  // Tags column - displays document tags as visual tag components
  columnHelper.accessor("tags", {
    header: "Tags",
    cell: (info) =>
      // Render each tag as a Chakra UI Tag component with margin spacing
      info.getValue()?.map((t) => (
        <Tag.Root key={t} mr={2}>
          <Tag.Label>{t}</Tag.Label>
        </Tag.Root>
      )),
  }),
];
