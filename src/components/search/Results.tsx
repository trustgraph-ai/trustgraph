import React, { useMemo, useCallback } from "react";
import { useNavigate } from "react-router";
import { Link } from "@chakra-ui/react";
import {
  createColumnHelper,
  useReactTable,
  getCoreRowModel,
} from "@tanstack/react-table";

// State management hooks and utilities
import { useWorkbenchStateStore } from "@trustgraph/react-state";
import { useSearchStateStore } from "@trustgraph/react-state";
import { Row } from "../../utils/row";
import ClickableTable from "../common/ClickableTable";
import { EmptyState } from "../common/TableStates";

// Create column helper for type-safe column definitions
const columnHelper = createColumnHelper<Row>();

/**
 * Results component displays search results in a table format
 * Shows entity name, description, and similarity score for each result
 * Allows navigation to individual entity detail pages
 */
const Results = () => {
  // Get search results from search state
  const rows = useSearchStateStore((state) => state.rows);

  // Get function to set selected entity in workbench
  const setSelected = useWorkbenchStateStore((state) => state.setSelected);

  // Hook for programmatic navigation
  const navigate = useNavigate();

  /**
   * Handles entity selection by setting the selected entity in state
   * and navigating to the entity detail page
   */
  const handleRowClick = useCallback(
    (row: Row) => {
      // Set selected entity with URI and label (fallback to 'n/a' if no label)
      setSelected({ uri: row.uri, label: row.label || "n/a" });
      // Navigate to entity detail page
      navigate("/entity");
    },
    [navigate, setSelected],
  );

  // Define table columns using TanStack table column helper
  const columns = useMemo(
    () => [
      columnHelper.accessor("label", {
        header: "Entity",
        cell: (info) => (
          <Link
            colorPalette="primary"
            onClick={(e) => {
              e.stopPropagation(); // Prevent row click from firing
              handleRowClick(info.row.original);
            }}
          >
            {info.getValue()}
          </Link>
        ),
      }),
      columnHelper.accessor("description", {
        header: "Description",
        cell: (info) => info.getValue() || "",
      }),
      columnHelper.accessor("similarity", {
        header: "Similarity",
        cell: (info) => {
          const value = info.getValue();
          return value ? value.toFixed(2) : "";
        },
      }),
    ],
    [handleRowClick],
  );

  // Create TanStack table instance
  const table = useReactTable({
    data: rows,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  // Handle empty state
  if (rows.length === 0) {
    return (
      <EmptyState message="No search results found. Try adjusting your search query." />
    );
  }

  // Render table with clickable rows
  return (
    <ClickableTable
      table={table}
      onClick={(row) => handleRowClick(row.original)}
      striped
      size="sm"
      mt={6}
    />
  );
};

export default Results;
