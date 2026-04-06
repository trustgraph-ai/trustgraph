import { useMemo } from "react";
import { getCoreRowModel, useReactTable } from "@tanstack/react-table";

import { columns, type McpTool } from "../../model/mcp-tools-table";
import ClickableTable from "../common/ClickableTable";

const McpToolsTable = ({ setSelected, tools }) => {
  // Transform the raw tools data to match our table structure
  const tableData: McpTool[] = useMemo(() => {
    return tools.map(([id, config]) => ({
      id,
      "remote-name": config?.["remote-name"] || "",
      url: config?.url || "",
    }));
  }, [tools]);

  // Initialize React Table with tool data and column configuration
  const table = useReactTable({
    data: tableData,
    columns: columns,
    getCoreRowModel: getCoreRowModel(),
  });

  const onSelect = (row) => {
    setSelected(row.original.id);
  };

  return <ClickableTable table={table} onClick={onSelect} />;
};

export default McpToolsTable;
