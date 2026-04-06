import { getCoreRowModel, useReactTable } from "@tanstack/react-table";

import { useFlows } from "@trustgraph/react-state";

import SelectableTable from "../common/SelectableTable";
import Actions from "./Actions";
import FlowControls from "./FlowControls";

import { columns } from "../../model/flow-table";

const Flows = () => {
  const flowState = useFlows();
  const flows = flowState.flows ? flowState.flows : [];

  // Initialize React Table with document data and column configuration
  const table = useReactTable({
    data: flows,
    columns: columns,
    getCoreRowModel: getCoreRowModel(),
  });

  // Get array of selected document IDs from the table selection
  const selected = table.getSelectedRowModel().rows.map((x) => x.original.id);

  const onDelete = () => {
    const ids = Array.from(selected);
    flowState.stopFlows({
      ids: ids,
      onSuccess: () => {
        table.setRowSelection({});
      },
    });
  };

  return (
    <>
      {/* Action buttons for bulk operations on selected documents */}
      <Actions selectedCount={selected.length} onDelete={onDelete} />

      {/* Main table displaying documents with selection capabilities */}
      <SelectableTable table={table} />

      {/* Controls for flow operations - create */}
      <FlowControls />
    </>
  );
};

export default Flows;
