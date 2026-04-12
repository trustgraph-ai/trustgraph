import { useCallback, useState } from "react";
import { useSocket } from "@/providers/socket-provider";
import { useSettings } from "@/providers/settings-provider";
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

export interface UploadProgress {
  phase: "preparing" | "uploading" | "finalizing";
  chunksTotal: number;
  chunksUploaded: number;
  bytesTotal: number;
  bytesUploaded: number;
}

export interface UseLibraryReturn {
  documents: DocumentMetadata[];
  processing: ProcessingMetadata[];
  loading: boolean;
  error: string | null;

  /** Refresh the documents list */
  getDocuments: () => Promise<void>;
  /** Upload a new document (auto-selects simple vs chunked based on size) */
  uploadDocument: (
    document: string,
    mimeType: string,
    title: string,
    comments: string,
    tags: string[],
    id?: string,
  ) => Promise<void>;
  /** Upload a large document using chunked upload with progress tracking */
  uploadDocumentChunked: (
    base64Content: string,
    mimeType: string,
    title: string,
    comments: string,
    tags: string[],
    onProgress?: (progress: UploadProgress) => void,
  ) => Promise<void>;
  /** Remove a document */
  removeDocument: (id: string, collection?: string) => Promise<void>;
  /** Get the list of currently-processing documents */
  getProcessing: () => Promise<void>;
  /** Fetch full metadata for a single document */
  getDocumentMetadata: (documentId: string) => Promise<DocumentMetadata | null>;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useLibrary(): UseLibraryReturn {
  const socket = useSocket();
  const user = useSettings((s) => s.settings.user);
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

  const uploadDocumentChunked = useCallback(
    async (
      base64Content: string,
      mimeType: string,
      title: string,
      comments: string,
      tags: string[],
      onProgress?: (progress: UploadProgress) => void,
    ) => {
      const act = "Upload document (chunked)";
      try {
        addActivity(act);
        const lib = socket.librarian();
        const totalSize = base64Content.length;

        onProgress?.({
          phase: "preparing",
          chunksTotal: 0,
          chunksUploaded: 0,
          bytesTotal: totalSize,
          bytesUploaded: 0,
        });

        // Begin the upload session
        const beginResp = await lib.beginUpload(
          {
            id: crypto.randomUUID(),
            time: Math.floor(Date.now() / 1000),
            kind: mimeType,
            title,
            comments,
            tags,
            user,
          },
          totalSize,
        );

        const uploadId = beginResp["upload-id"];
        const chunkSize = beginResp["chunk-size"];
        const totalChunks = beginResp["total-chunks"];

        // Upload chunks sequentially
        let bytesUploaded = 0;
        for (let i = 0; i < totalChunks; i++) {
          const start = i * chunkSize;
          const end = Math.min(start + chunkSize, totalSize);
          const chunk = base64Content.slice(start, end);

          await lib.uploadChunk(uploadId, i, chunk);
          bytesUploaded += chunk.length;

          onProgress?.({
            phase: "uploading",
            chunksTotal: totalChunks,
            chunksUploaded: i + 1,
            bytesTotal: totalSize,
            bytesUploaded,
          });
        }

        // Finalize
        onProgress?.({
          phase: "finalizing",
          chunksTotal: totalChunks,
          chunksUploaded: totalChunks,
          bytesTotal: totalSize,
          bytesUploaded: totalSize,
        });

        await lib.completeUpload(uploadId);
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

  const getDocumentMetadata = useCallback(
    async (documentId: string): Promise<DocumentMetadata | null> => {
      try {
        return await socket.librarian().getDocumentMetadata(documentId);
      } catch (err) {
        console.error("useLibrary.getDocumentMetadata error:", err);
        return null;
      }
    },
    [socket],
  );

  return {
    documents,
    processing,
    loading,
    error,
    getDocuments,
    uploadDocument,
    uploadDocumentChunked,
    removeDocument,
    getProcessing,
    getDocumentMetadata,
  };
}
