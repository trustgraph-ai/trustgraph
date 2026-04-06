import React from "react";
import { getCoreRowModel, useReactTable } from "@tanstack/react-table";

import BasicTable from "../common/BasicTable";
import {
  columns,
  NodeRelationship,
} from "../../model/node-relationships-table";

interface RelationshipsTableProps {
  outboundRelationships: Array<{
    uri: string;
    label: string;
  }>;
  inboundRelationships: Array<{
    uri: string;
    label: string;
  }>;
  onRelationshipClick: (
    relationshipUri: string,
    direction: "incoming" | "outgoing",
  ) => void;
}

const RelationshipsTable: React.FC<RelationshipsTableProps> = ({
  outboundRelationships,
  inboundRelationships,
  onRelationshipClick,
}) => {
  // Combine and transform relationships data to match the NodeRelationship interface
  const tableData: NodeRelationship[] = [
    // Add outbound relationships
    ...outboundRelationships.map((rel) => ({
      relationship: rel.label,
      direction: "outgoing" as const,
      uri: rel.uri,
      onRelationshipClick: (uri: string) =>
        onRelationshipClick(uri, "outgoing"),
    })),
    // Add inbound relationships
    ...inboundRelationships.map((rel) => ({
      relationship: rel.label,
      direction: "incoming" as const,
      uri: rel.uri,
      onRelationshipClick: (uri: string) =>
        onRelationshipClick(uri, "incoming"),
    })),
  ];

  // Initialize React Table with relationships data and column configuration
  const table = useReactTable({
    data: tableData,
    columns: columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return <BasicTable table={table} />;
};

export default RelationshipsTable;
