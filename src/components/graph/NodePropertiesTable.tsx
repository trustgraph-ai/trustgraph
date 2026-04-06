import React from "react";
import { getCoreRowModel, useReactTable } from "@tanstack/react-table";

import BasicTable from "../common/BasicTable";
import { columns, NodeProperty } from "../../model/node-properties-table";

interface NodePropertiesTableProps {
  properties: Array<{
    predicate: {
      uri: string;
      label: string;
    };
    value: string;
  }>;
}

const NodePropertiesTable: React.FC<NodePropertiesTableProps> = ({
  properties,
}) => {
  // Transform properties data to match the NodeProperty interface
  const tableData: NodeProperty[] = properties.map((prop) => ({
    property: prop.predicate.label,
    value: prop.value,
    uri: prop.predicate.uri,
  }));

  // Initialize React Table with properties data and column configuration
  const table = useReactTable({
    data: tableData,
    columns: columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return <BasicTable table={table} />;
};

export default NodePropertiesTable;
