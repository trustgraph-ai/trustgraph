import React, { useState } from "react";

import { getCoreRowModel, useReactTable } from "@tanstack/react-table";

import { columns } from "../../model/document-table";
import {
  useLibrary,
  useNotification,
  useSettings,
} from "@trustgraph/react-state";

import Actions from "./Actions";
import SubmitDialog from "./SubmitDialog";
import SelectableTable from "../common/SelectableTable";
import DocumentControls from "./DocumentControls";
import UploadDialog from "../load/UploadDialog";

/**
 * Documents component - Main container for document management interface
 * Handles document listing, selection, submission, deletion, and upload
 * operations
 */
const Documents = () => {
  // State for controlling the submit dialog visibility
  const [submitOpen, setSubmitOpen] = useState(false);

  // State for controlling the upload dialog visibility
  const [uploadOpen, setUploadOpen] = useState(false);

  // Hook for displaying notifications to the user
  const notify = useNotification();

  // Hook for accessing settings
  const { settings } = useSettings();

  // Hook for accessing library state and operations
  const library = useLibrary();

  // Get documents from library state, fallback to empty array if undefined
  const documents = library.documents ? library.documents : [];

  // Initialize React Table with document data and column configuration
  const table = useReactTable({
    data: documents,
    columns: columns,
    getCoreRowModel: getCoreRowModel(),
  });

  // Get array of selected document IDs from the table selection
  const selected = table.getSelectedRowModel().rows.map((x) => x.original.id);

  /**
   * Delete multiple documents by their IDs
   * Clears table selection on successful deletion
   * @param {Array} ids - Array of document IDs to delete
   */
  const deleteDocuments = (ids) =>
    library.deleteDocuments({
      ids: ids,
      onSuccess: () => {
        // Clear row selection after successful deletion
        table.setRowSelection({});
      },
    });

  /**
   * Submit multiple documents to a workflow with tags
   * Clears selection and closes submit dialog on success
   * @param {Array} ids - Array of document IDs to submit
   * @param {string} flow - Workflow identifier
   * @param {Array} tags - Array of tags to apply
   */
  const submitDocuments = (ids, flow, tags) =>
    library.submitDocuments({
      ids: ids,
      flow: flow,
      tags: tags,
      collection: settings?.collection || "default",
      onSuccess: () => {
        // Clear selection and close dialog after successful submission
        table.setRowSelection({});
        setSubmitOpen(false);
      },
    });

  /**
   * Handle submit confirmation from the submit dialog
   * @param {string} flow - Selected workflow
   * @param {Array} tags - Selected tags
   */
  const onConfirmSubmit = (flow, tags) => {
    submitDocuments(selected, flow, tags);
  };

  /**
   * Handle edit action for selected documents
   * Currently shows "Not implemented" notification
   */
  const onEdit = () => {
    notify.info("Not implemented");
  };

  /**
   * Handle delete action for selected documents
   */
  const onDelete = () => {
    deleteDocuments(selected);
  };

  return (
    <>
      {/* Action buttons for bulk operations on selected documents */}
      <Actions
        selectedCount={selected.length}
        onSubmit={() => setSubmitOpen(true)}
        onEdit={onEdit}
        onDelete={onDelete}
      />

      {/* Dialog for submitting documents to workflows */}
      <SubmitDialog
        open={submitOpen}
        onOpenChange={setSubmitOpen}
        onSubmit={onConfirmSubmit}
        docs={table.getSelectedRowModel().rows.map((x) => x.original)}
      />

      {/* Dialog for uploading new documents */}
      <UploadDialog open={uploadOpen} onOpenChange={setUploadOpen} />

      {/* Main table displaying documents with selection capabilities */}
      <SelectableTable table={table} />

      {/* Controls for document operations like upload */}
      <DocumentControls onUpload={() => setUploadOpen(true)} />
    </>
  );
};

export default Documents;
