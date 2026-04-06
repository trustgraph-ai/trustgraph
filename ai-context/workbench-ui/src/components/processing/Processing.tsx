import { getCoreRowModel, useReactTable } from "@tanstack/react-table";

import { useProcessing } from "@trustgraph/react-state";
import BasicTable from "../common/BasicTable";

import { columns } from "../../model/processing-table";

const ProcessingTable = () => {
  // Processing state
  const processingState = useProcessing();
  const processing = processingState.processing
    ? processingState.processing
    : [];

  // Initialize React Table with document data and column configuration
  const table = useReactTable({
    data: processing,
    columns: columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return <BasicTable table={table} />;
};

export default ProcessingTable;
