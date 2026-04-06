import React, { useState } from "react";

import { getCoreRowModel, useReactTable } from "@tanstack/react-table";

import { columns } from "../../model/knowledge-core-table";
import { useKnowledgeCores } from "@trustgraph/react-state";
import { useSettings } from "@trustgraph/react-state";
import { createAuthenticatedFetch } from "../../api/authenticated-fetch";

import SelectableTable from "../common/SelectableTable";
import Actions from "./Actions";
import Controls from "./Controls";
import LoadDialog from "./LoadDialog";

const KnowledgeCores = () => {
  const state = useKnowledgeCores();
  const { settings } = useSettings();

  const knowledgeCores = state.knowledgeCores ? state.knowledgeCores : [];

  const [loadDialogOpen, setLoadDialogOpen] = useState(false);

  // Initialize React Table with document data and column configuration
  const table = useReactTable({
    data: knowledgeCores,
    columns: columns,
    getCoreRowModel: getCoreRowModel(),
  });

  // Get array of selected document IDs from the table selection
  const selected = table.getSelectedRowModel().rows.map((x) => x.original.id);

  const onDelete = () => {
    state.deleteKnowledgeCores({
      ids: selected,
      onSuccess: () => {
        // Clear row selection after successful deletion
        table.setRowSelection({});
      },
    });
  };

  const onDownload = async () => {
    const sels = Array.from(selected);
    const authenticatedFetch = createAuthenticatedFetch(
      settings.authentication.apiKey,
    );

    for (const sel of sels) {
      const fname =
        sel
          .replace("https://", "")
          .replace("http://", "")
          .replace(/[ :/]/g, "-")
          .replace(/[^-a-zA-Z0-9.]/g, "")
          .substr(0, 15) + ".core";

      const url =
        "/api/export-core?" +
        "id=" +
        encodeURIComponent(sel) + // Fixed: was using sels[0] instead of sel
        "&user=" +
        encodeURIComponent("trustgraph");

      try {
        // Use authenticated fetch to download the file
        const response = await authenticatedFetch(url);

        if (!response.ok) {
          throw new Error(
            `Download failed: ${response.status} ${response.statusText}`,
          );
        }

        // Convert response to blob and download
        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);

        const link = document.createElement("a");
        link.href = downloadUrl;
        link.download = fname;
        link.click();

        // Clean up the blob URL
        window.URL.revokeObjectURL(downloadUrl);
      } catch (error) {
        console.error("Download failed for", sel, error);
        // TODO: Show error notification to user
      }
    }
  };

  const onLoad = () => {
    setLoadDialogOpen(true);
  };

  const handleLoad = (ids, flow) => {
    state.loadKnowledgeCores({
      ids: ids,
      flow: flow,
      onSuccess: () => {
        // Clear row selection after successful load
        table.setRowSelection({});
      },
    });
  };

  return (
    <>
      <Actions
        selectedCount={selected.length}
        onDelete={onDelete}
        onDownload={onDownload}
        onLoad={onLoad}
      />

      <SelectableTable table={table} />

      <Controls />

      <LoadDialog
        open={loadDialogOpen}
        onOpenChange={setLoadDialogOpen}
        selectedIds={selected}
        onLoad={handleLoad}
      />
    </>
  );
};

export default KnowledgeCores;
