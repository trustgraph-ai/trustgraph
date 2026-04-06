import { createColumnHelper } from "@tanstack/react-table";
import { Code } from "@chakra-ui/react";

/**
 * Prompt data structure for the prompts table
 * Represents a prompt template with its metadata and configuration
 */
export type Prompt = {
  id: string; // Unique identifier for the prompt template
  prompt: string; // The prompt text content
  responseType: "json" | "text"; // Type of response expected
  hasSchema: boolean; // Whether the prompt has a schema defined
};

// Create a column helper instance for type-safe column definitions
export const columnHelper = createColumnHelper<Prompt>();

/**
 * Column definitions for the prompts table
 * Defines how each column should be rendered and what data it displays
 */
export const columns = [
  // ID column - displays the prompt template ID
  columnHelper.accessor("id", {
    header: "ID",
    cell: (info) => <Code p={2}>{info.getValue()}</Code>,
  }),

  // Prompt column - displays the prompt text content
  columnHelper.accessor("prompt", {
    header: "Prompt",
    cell: (info) => <Code p={2}>{info.getValue()}</Code>,
  }),

  // Response type column - displays the expected response format
  columnHelper.accessor("responseType", {
    header: "Response",
    cell: (info) => {
      const value = info.getValue();
      return value === "json" ? "JSON" : "text";
    },
  }),

  // Schema column - displays whether the prompt has a schema
  columnHelper.accessor("hasSchema", {
    header: "Schema?",
    cell: (info) => (info.getValue() ? "yes" : "no"),
  }),
];
