import { createColumnHelper } from "@tanstack/react-table";

/**
 * MCP Tool data structure for the tools table
 * Represents an MCP tool with its configuration
 */
export type McpTool = {
  id: string; // Unique identifier for the tool
  "remote-name": string; // Remote name of the MCP tool
  url: string; // MCP endpoint URL
};

// Create a column helper instance for type-safe column definitions
export const columnHelper = createColumnHelper<McpTool>();

/**
 * Column definitions for the MCP tools table
 * Defines how each column should be rendered and what data it displays
 */
export const columns = [
  // Tool ID column - displays the tool identifier
  columnHelper.accessor("id", {
    header: "Tool ID",
    cell: (info) => info.getValue(),
  }),

  // Remote Name column - displays the remote tool name
  columnHelper.accessor("remote-name", {
    header: "Remote Name",
    cell: (info) => info.getValue(),
  }),

  // URL column - displays the MCP endpoint URL
  columnHelper.accessor("url", {
    header: "MCP Endpoint URL",
    cell: (info) => info.getValue(),
  }),
];
