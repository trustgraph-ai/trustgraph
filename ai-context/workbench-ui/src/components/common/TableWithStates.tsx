import React from "react";
import { Box } from "@chakra-ui/react";
import { Table } from "@tanstack/react-table";
import { ErrorState, EmptyState } from "./TableStates";
import BasicTable from "./BasicTable";
import ClickableTable from "./ClickableTable";

interface TableWithStatesProps<T> {
  table: Table<T>;
  data: T[];
  error?: Error | unknown;
  onClick?: (row: T) => void;
  emptyMessage?: string;
  errorTitle?: string;
  bordered?: boolean;
}

const TableWithStates = <T,>({
  table,
  data,
  error,
  onClick,
  emptyMessage = "No data found.",
  errorTitle = "Error loading data",
  bordered = true,
}: TableWithStatesProps<T>) => {
  // Handle error state
  if (error) {
    return <ErrorState error={error} title={errorTitle} />;
  }

  // Handle empty state
  if (data.length === 0) {
    return <EmptyState message={emptyMessage} />;
  }

  // Render table with optional border wrapper
  const TableComponent = onClick ? (
    <ClickableTable table={table} onClick={(row) => onClick(row.original)} />
  ) : (
    <BasicTable table={table} />
  );

  if (bordered) {
    return (
      <Box overflowX="auto" borderWidth="1px" borderRadius="lg">
        {TableComponent}
      </Box>
    );
  }

  return TableComponent;
};

export default TableWithStates;
