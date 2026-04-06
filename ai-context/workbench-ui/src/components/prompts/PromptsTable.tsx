import { useMemo } from "react";
import { getCoreRowModel, useReactTable } from "@tanstack/react-table";

import { columns, type Prompt } from "../../model/prompts-table";
import ClickableTable from "../common/ClickableTable";

const PromptsTable = ({ prompts, onSelect }) => {
  // Transform the raw prompts data to match our table structure
  const tableData: Prompt[] = useMemo(() => {
    return prompts.map(([id, config]) => ({
      id,
      prompt: config?.prompt || "",
      responseType: config?.["response-type"] === "json" ? "json" : "text",
      hasSchema: Boolean(config?.schema),
    }));
  }, [prompts]);

  // Initialize React Table with prompt data and column configuration
  const table = useReactTable({
    data: tableData,
    columns: columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <ClickableTable
      table={table}
      onClick={(row) =>
        onSelect([
          row.original.id,
          prompts.find(([id]) => id === row.original.id)?.[1],
        ])
      }
    />
  );
};

export default PromptsTable;
