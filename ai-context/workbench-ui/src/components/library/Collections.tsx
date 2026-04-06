import React, { useState } from "react";

import { getCoreRowModel, useReactTable } from "@tanstack/react-table";

import { columns } from "../../model/collection-table";
import { useCollections } from "@trustgraph/react-state";
import { useNotification } from "@trustgraph/react-state";

import CollectionActions from "./CollectionActions";
import CollectionDialog from "./CollectionDialog";
import SelectableTable from "../common/SelectableTable";
import CollectionControls from "./CollectionControls";

/**
 * Collections component - Main container for collection management interface
 * Handles collection listing, selection, creation, editing, and deletion operations
 */
const Collections = () => {
  // State for controlling the collection dialog visibility
  const [dialogOpen, setDialogOpen] = useState(false);

  // State for tracking which collection is being edited (null for creating new)
  const [editingCollection, setEditingCollection] = useState(null);

  // Hook for displaying notifications to the user
  const notify = useNotification();

  // Hook for accessing collections state and operations
  const collectionsState = useCollections();

  // Get collections from state, fallback to empty array if undefined
  const collections = collectionsState.collections || [];

  // Initialize React Table with collection data and column configuration
  const table = useReactTable({
    data: collections,
    columns: columns,
    getCoreRowModel: getCoreRowModel(),
  });

  // Get array of selected collection IDs from the table selection
  const selected = table
    .getSelectedRowModel()
    .rows.map((x) => x.original.collection);

  /**
   * Handle creating a new collection
   * Opens the dialog in create mode (no editing collection set)
   */
  const onCreateNew = () => {
    setEditingCollection(null);
    setDialogOpen(true);
  };

  /**
   * Handle editing a selected collection
   * Opens the dialog in edit mode with the selected collection data
   */
  const onEdit = () => {
    if (selected.length !== 1) {
      notify.info("Please select exactly one collection to edit");
      return;
    }
    const collection = collections.find((c) => c.collection === selected[0]);
    setEditingCollection(collection);
    setDialogOpen(true);
  };

  /**
   * Handle deleting selected collections
   */
  const onDelete = () => {
    collectionsState.deleteCollections({
      collections: selected,
      onSuccess: () => {
        // Clear row selection after successful deletion
        table.setRowSelection({});
      },
    });
  };

  /**
   * Handle saving a collection (create or update)
   * @param {string} collection - Collection ID
   * @param {string} name - Display name
   * @param {string} description - Description text
   * @param {Array} tags - Array of tags
   */
  const onSaveCollection = (collection, name, description, tags) => {
    collectionsState.updateCollection({
      collection,
      name,
      description,
      tags,
      onSuccess: () => {
        // Close dialog and clear selection after successful save
        setDialogOpen(false);
        table.setRowSelection({});
      },
    });
  };

  return (
    <>
      {/* Action buttons for bulk operations on selected collections */}
      <CollectionActions
        selectedCount={selected.length}
        onEdit={onEdit}
        onDelete={onDelete}
      />

      {/* Dialog for creating/editing collections */}
      <CollectionDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onSave={onSaveCollection}
        editingCollection={editingCollection}
      />

      {/* Main table displaying collections with selection capabilities */}
      <SelectableTable table={table} />

      {/* Controls for collection operations like create */}
      <CollectionControls onCreate={onCreateNew} />
    </>
  );
};

export default Collections;
