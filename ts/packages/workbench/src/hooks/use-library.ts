import { useCallback, useState } from "react";
import { useSocket } from "@/providers/socket-provider";
import { useProgressStore } from "./use-progress-store";
import type { DocumentMetadata } from "@trustgraph/client";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ProcessingMetadata {
  id: string;
  "document-id": string;
  flow: string;
  collection: string;
  [key: string]: unknown;
}

export interface UseLibraryReturn {
  documents: DocumentMetadata[];
  processing: ProcessingMetadata[];
  loading: boolean;
  error: string | null;

  /** Refresh the documents list */
  getDocuments: () => Promise<void>;
  /** Upload a new document */
  uploadDocument: (
    document: string,
    mimeType: string,
    title: string,
    comments: string,
    tags: string[],
    id?: string,
  ) => Promise<void>;
  /** Remove a document */
  removeDocument: (id: string, collection?: string) => Promise<void>;
  /** Get the list of currently-processing documents */
  getProcessing: () => Promise<void>;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useLibrary(): UseLibraryReturn {
  const socket = useSocket();
  const addActivity = useProgressStore((s) => s.addActivity);
  const removeActivity = useProgressStore((s) => s.removeActivity);

  const [documents, setDocuments] = useState<DocumentMetadata[]>([]);
  const [processing, setProcessing] = useState<ProcessingMetadata[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getDocuments = useCallback(async () => {
    const act = "Load documents";
    try {
      setLoading(true);
      setError(null);
      addActivity(act);
      const docs = await socket.librarian().getDocuments();
      setDocuments(docs);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
      console.error("useLibrary.getDocuments error:", err);
    } finally {
      setLoading(false);
      removeActivity(act);
    }
  }, [socket, addActivity, removeActivity]);

  const uploadDocument = useCallback(
    async (
      document: string,
      mimeType: string,
      title: string,
      comments: string,
      tags: string[],
      id?: string,
    ) => {
      const act = "Upload document";
      try {
        addActivity(act);
        await socket
          .librarian()
          .loadDocument(document, mimeType, title, comments, tags, id);
        // Refresh list after upload
        await getDocuments();
      } finally {
        removeActivity(act);
      }
    },
    [socket, addActivity, removeActivity, getDocuments],
  );

  const removeDocument = useCallback(
    async (id: string, collection?: string) => {
      const act = "Remove document";
      try {
        addActivity(act);
        await socket.librarian().removeDocument(id, collection);
        await getDocuments();
      } finally {
        removeActivity(act);
      }
    },
    [socket, addActivity, removeActivity, getDocuments],
  );

  const getProcessing = useCallback(async () => {
    const act = "Load processing";
    try {
      addActivity(act);
      const procs = await socket.librarian().getProcessing();
      setProcessing(procs as ProcessingMetadata[]);
    } catch (err) {
      console.error("useLibrary.getProcessing error:", err);
    } finally {
      removeActivity(act);
    }
  }, [socket, addActivity, removeActivity]);

  return {
    documents,
    processing,
    loading,
    error,
    getDocuments,
    uploadDocument,
    removeDocument,
    getProcessing,
  };
}
