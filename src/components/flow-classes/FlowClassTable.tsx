import React from "react";
import { getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { Box } from "@chakra-ui/react";

import {
  useFlowClasses,
  generateFlowClassId,
  FlowClassDefinition,
} from "@trustgraph/react-state";
import { flowClassColumns, FlowClassRow } from "../../model/flow-class-table";

import SelectableTable from "../common/SelectableTable";
import FlowClassActions from "./FlowClassActions";
import FlowClassControls from "./FlowClassControls";

interface FlowClassTableProps {
  onEdit?: (flowClassId: string) => void;
}

const FlowClassTable: React.FC<FlowClassTableProps> = ({ onEdit }) => {
  const { flowClasses, createFlowClass, deleteFlowClass, duplicateFlowClass } =
    useFlowClasses();

  // No need for selected flow class state - actions handled by ActionBar

  // Transform flow classes data if it's in [key, value] format
  const transformedFlowClasses = React.useMemo(() => {
    if (!flowClasses || !Array.isArray(flowClasses)) return [];

    // Check if first item is an array [key, value] pair
    if (
      flowClasses.length > 0 &&
      Array.isArray(flowClasses[0]) &&
      flowClasses[0].length === 2
    ) {
      return flowClasses.map(([id, flowClass]) => ({
        id,
        ...(flowClass as Omit<FlowClassDefinition, "id">),
      }));
    }

    // Already transformed
    return flowClasses;
  }, [flowClasses]);

  // Initialize React Table with flow class data and column configuration
  const table = useReactTable({
    data: (transformedFlowClasses as FlowClassRow[]) || [],
    columns: flowClassColumns,
    getCoreRowModel: getCoreRowModel(),
  });

  // Get array of selected flow class IDs from the table selection
  const selectedRows = table.getSelectedRowModel().rows;
  const selectedIds = selectedRows.map((row) => row.original.id!);
  const selectedCount = selectedIds.length;

  const handleEdit = () => {
    if (selectedRows.length === 1) {
      const flowClassId = selectedRows[0].original.id;
      onEdit?.(flowClassId);
    }
  };

  const handleDuplicate = async () => {
    if (selectedRows.length === 1) {
      const sourceId = selectedRows[0].original.id!;
      const targetId = generateFlowClassId(`${sourceId}-copy`);

      try {
        await duplicateFlowClass({ sourceId, targetId });
        table.setRowSelection({});
      } catch (error) {
        console.error("Failed to duplicate flow class:", error);
      }
    }
  };

  const handleDelete = async () => {
    if (selectedIds.length > 0) {
      await Promise.all(selectedIds.map((id) => deleteFlowClass(id)));
      table.setRowSelection({});
    }
  };

  const handleNew = async (id: string) => {
    const newFlowClass = {
      class: {},
      flow: {},
      interfaces: {},
      description: "New flow class",
      tags: [],
    };

    try {
      await createFlowClass({ id, flowClass: newFlowClass });
    } catch (error) {
      console.error("Failed to create flow class:", error);
    }
  };

  // Removed edit panel handlers - no longer needed

  return (
    <Box position="relative">
      {/* Action buttons for bulk operations on selected flow classes */}
      <FlowClassActions
        selectedCount={selectedCount}
        onEdit={handleEdit}
        onDuplicate={handleDuplicate}
        onDelete={handleDelete}
      />

      {/* Main table displaying flow classes with selection capabilities */}
      <SelectableTable table={table} />

      {/* Controls for flow class operations - create */}
      <FlowClassControls onNew={handleNew} />

      {/* No edit panel needed - actions are handled by the ActionBar */}
    </Box>
  );
};

export default FlowClassTable;
