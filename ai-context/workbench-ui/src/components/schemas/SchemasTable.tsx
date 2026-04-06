import React from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
} from "@tanstack/react-table";
import { useSchemas } from "@trustgraph/react-state";
import { SchemaTableRow, schemaColumns } from "../../model/schemas-table";
import { EditSchemaDialog } from "./EditSchemaDialog";
import TableWithStates from "../common/TableWithStates";

export const SchemasTable: React.FC = () => {
  const { schemas, schemasError } = useSchemas();
  const [isOpen, setIsOpen] = React.useState(false);
  const [selectedSchema, setSelectedSchema] =
    React.useState<SchemaTableRow | null>(null);

  const table = useReactTable({
    data: schemas as SchemaTableRow[],
    columns: schemaColumns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  const handleRowClick = (row: SchemaTableRow) => {
    setSelectedSchema(row);
    setIsOpen(true);
  };

  // Loading state is handled by useActivity in the schemas hook
  // CenterSpinner component automatically shows when activities are active

  return (
    <>
      <TableWithStates
        table={table}
        data={schemas}
        error={schemasError}
        onClick={handleRowClick}
        emptyMessage="No schemas found. Create one to get started."
        errorTitle="Error loading schemas"
      />

      {selectedSchema && (
        <EditSchemaDialog
          isOpen={isOpen}
          onClose={() => setIsOpen(false)}
          mode="edit"
          schemaId={selectedSchema[0]}
          initialSchema={selectedSchema[1]}
        />
      )}
    </>
  );
};
