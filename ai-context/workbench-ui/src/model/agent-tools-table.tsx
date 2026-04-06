import { createColumnHelper } from "@tanstack/react-table";

/**
 * Agent Tool data structure for the tools table
 * Represents an agent tool with its metadata and configuration
 */
export type AgentTool = {
  id: string; // Unique identifier for the tool
  name: string; // Human-readable name for the tool
  description: string; // Description of what the tool does
  type: string; // Type of the tool
};

// Create a column helper instance for type-safe column definitions
export const columnHelper = createColumnHelper<AgentTool>();

/**
 * Column definitions for the agent tools table
 * Defines how each column should be rendered and what data it displays
 */
export const columns = [
  // Tool ID column - displays the tool identifier
  columnHelper.accessor("id", {
    header: "Tool ID",
    cell: (info) => info.getValue(),
  }),

  // Name column - displays the human-readable tool name
  columnHelper.accessor("name", {
    header: "Name",
    cell: (info) => info.getValue(),
  }),

  // Description column - displays the tool description
  columnHelper.accessor("description", {
    header: "Description",
    cell: (info) => info.getValue(),
  }),

  // Type column - displays the tool type
  columnHelper.accessor("type", {
    header: "Type",
    cell: (info) => info.getValue(),
  }),
];
