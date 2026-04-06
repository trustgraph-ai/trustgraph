import { createColumnHelper } from "@tanstack/react-table";
import { Tag } from "@chakra-ui/react";
import { timeString } from "../utils/time-string.ts";

/**
 * Processing data structure for the processing table
 * Represents a single processing object with its metadata and properties
 */
export type Processing = {
  id: string; // Unique identifier for the processing
  time: number; // Timestamp (likely Unix timestamp)
  document: string; // Document ID
  tags: string[]; // Array of tags associated with the document
};

// Create a column helper instance for type-safe column definitions
export const columnHelper = createColumnHelper<Processing>();

/**
 * Column definitions for the processing table
 * Defines how each column should be rendered and what data it displays
 */
export const columns = [
  // ID column - displays the flow ID
  columnHelper.accessor("id", {
    header: "ID",
    cell: (info) => info.getValue(),
  }),

  // Time column - displays formatted timestamp
  columnHelper.accessor("time", {
    header: "Time",
    cell: (info) => timeString(info.getValue()), // Convert to readable string
  }),

  // Class name column - displays flow class
  columnHelper.accessor("document-id", {
    header: "Document ID",
    cell: (info) => info.getValue(),
  }),

  // Class name column - displays flow class
  columnHelper.accessor("flow", {
    header: "Flow ID",
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
