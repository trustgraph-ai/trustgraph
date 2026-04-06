import { useMemo } from "react";
import { getCoreRowModel, useReactTable } from "@tanstack/react-table";

import { columns, type AgentTool } from "../../model/agent-tools-table";
import ClickableTable from "../common/ClickableTable";

const ToolsTable = ({ setSelected, tools }) => {
  // Transform the raw tools data to match our table structure
  const tableData: AgentTool[] = useMemo(() => {
    return tools.map(([id, config]) => ({
      id,
      name: config?.name || "",
      description: config?.description || "",
      type: config?.type || "",
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

export default ToolsTable;
