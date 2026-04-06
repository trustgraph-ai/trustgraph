import { createColumnHelper } from "@tanstack/react-table";

/**
 * Processing data structure for the processing table
 * Represents a single processing object with its metadata and properties
 */
export type TokenCost = {
  modeel: string; // Unique identifier for the processing
  inputPrice: number; // Per-input token cost
  outputPrice: number; // Per-output token cost
};

// Create a column helper instance for type-safe column definitions
export const columnHelper = createColumnHelper<TokenCost>();

/**
 * Column definitions for the processing table
 * Defines how each column should be rendered and what data it displays
 */
export const columns = [
  // Model column - displays the model ID
  columnHelper.accessor("model", {
    header: "Model ID",
    cell: (info) => info.getValue(),
  }),

  // Input token column - displays input token cost
  columnHelper.accessor("input_price", {
    header: "Input cost ($/1Mt)",
    cell: (info) => (info.getValue() * 1000000).toFixed(3),
  }),

  // Input token column - displays input token cost
  columnHelper.accessor("output_price", {
    header: "Output cost ($/1Mt)",
    cell: (info) => (info.getValue() * 1000000).toFixed(3),
  }),
];
