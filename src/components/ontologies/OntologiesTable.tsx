import React, { useState } from "react";
import {
  Box,
  Table,
  Text,
  Spinner,
  Center,
  Button,
  HStack,
} from "@chakra-ui/react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
} from "@tanstack/react-table";
import { useOntologies } from "@trustgraph/react-state";
import {
  OntologyTableRow,
  ontologyColumns,
} from "../../model/ontologies-table";
import { CreateOntologyDialog } from "./CreateOntologyDialog";
import { ConfirmDialog } from "../common/ConfirmDialog";
import { ImportDialog } from "./ImportDialog";
import { Upload } from "lucide-react";

interface OntologiesTableProps {
  onEditOntology?: (ontologyId: string) => void;
}

export const OntologiesTable: React.FC<OntologiesTableProps> = ({
  onEditOntology,
}) => {
  const { ontologies, ontologiesLoading, ontologiesError, deleteOntology } =
    useOntologies();
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isImportDialogOpen, setIsImportDialogOpen] = useState(false);
  const [confirmDialog, setConfirmDialog] = useState<{
    isOpen: boolean;
    ontologyId: string;
  }>({
    isOpen: false,
    ontologyId: "",
  });

  const table = useReactTable({
    data: ontologies as OntologyTableRow[],
    columns: ontologyColumns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  const handleRowClick = (row: OntologyTableRow) => {
    if (onEditOntology) {
      onEditOntology(row[0]);
    }
  };

  const handleDelete = (ontologyId: string, event: React.MouseEvent) => {
    event.stopPropagation(); // Prevent row click

    setConfirmDialog({
      isOpen: true,
      ontologyId,
    });
  };

  const handleConfirmDelete = () => {
    deleteOntology({ id: confirmDialog.ontologyId });
    setConfirmDialog({ isOpen: false, ontologyId: "" });
  };

  const handleCreateOntology = (ontologyId: string) => {
    setIsCreateDialogOpen(false);
    if (onEditOntology) {
      // Small delay to allow the dialog to close first
      setTimeout(() => onEditOntology(ontologyId), 100);
    }
  };

  const handleImportOntology = (ontologyId: string) => {
    setIsImportDialogOpen(false);
    if (onEditOntology) {
      // Small delay to allow the dialog to close first
      setTimeout(() => onEditOntology(ontologyId), 100);
    }
  };

  if (ontologiesLoading) {
    return (
      <Center h="200px">
        <Spinner size="xl" />
      </Center>
    );
  }

  if (ontologiesError) {
    return (
      <Box
        p={4}
        borderWidth="1px"
        borderColor="red.500"
        borderRadius="md"
        bg="red.50"
      >
        <Text color="red.700">
          Error loading ontologies: {ontologiesError.toString()}
        </Text>
      </Box>
    );
  }

  return (
    <>
      <Box mb={4}>
        <HStack>
          <Button
            colorPalette="primary"
            onClick={() => setIsCreateDialogOpen(true)}
          >
            Create New Ontology
          </Button>
          <Button
            variant="outline"
            onClick={() => setIsImportDialogOpen(true)}
          >
            <Upload size={16} style={{ marginRight: "8px" }} />
            Import Ontology
          </Button>
        </HStack>
      </Box>

      {ontologies.length === 0 ? (
        <Center h="200px">
          <Text color="gray.500">
            No ontologies found. Create one to get started.
          </Text>
        </Center>
      ) : (
        <Box overflowX="auto" borderWidth="1px" borderRadius="lg">
          <Table.Root interactive>
            <Table.Header>
              {table.getHeaderGroups().map((headerGroup) => (
                <Table.Row key={headerGroup.id}>
                  {headerGroup.headers.map((header) => (
                    <Table.ColumnHeader key={header.id}>
                      {header.isPlaceholder
                        ? null
                        : flexRender(
                            header.column.columnDef.header,
                            header.getContext(),
                          )}
                    </Table.ColumnHeader>
                  ))}
                  <Table.ColumnHeader>Actions</Table.ColumnHeader>
                </Table.Row>
              ))}
            </Table.Header>
            <Table.Body>
              {table.getRowModel().rows.map((row) => (
                <Table.Row
                  key={row.id}
                  onClick={() => handleRowClick(row.original)}
                  style={{ cursor: "pointer" }}
                >
                  {row.getVisibleCells().map((cell) => (
                    <Table.Cell key={cell.id}>
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext(),
                      )}
                    </Table.Cell>
                  ))}
                  <Table.Cell>
                    <Button
                      size="sm"
                      colorPalette="red"
                      variant="ghost"
                      onClick={(e) => handleDelete(row.original[0], e)}
                    >
                      Delete
                    </Button>
                  </Table.Cell>
                </Table.Row>
              ))}
            </Table.Body>
          </Table.Root>
        </Box>
      )}

      <CreateOntologyDialog
        isOpen={isCreateDialogOpen}
        onClose={() => setIsCreateDialogOpen(false)}
        onCreated={handleCreateOntology}
      />

      <ImportDialog
        isOpen={isImportDialogOpen}
        onClose={() => setIsImportDialogOpen(false)}
        onImported={handleImportOntology}
      />

      <ConfirmDialog
        isOpen={confirmDialog.isOpen}
        onClose={() => setConfirmDialog({ isOpen: false, ontologyId: "" })}
        onConfirm={handleConfirmDelete}
        title="Delete Ontology"
        message={`Are you sure you want to delete the ontology "${confirmDialog.ontologyId}"?\n\nThis action cannot be undone and will permanently remove all classes, properties, and metadata.`}
        variant="danger"
        confirmText="Delete"
      />
    </>
  );
};
