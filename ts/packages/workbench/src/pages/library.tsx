import { useCallback, useEffect, useRef, useState } from "react";
import {
  LibraryBig,
  Upload,
  Trash2,
  RefreshCw,
  FileText,
  FileType2,
  Loader2,
  X,
  AlertTriangle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useLibrary } from "@/hooks/use-library";
import { useSettings } from "@/providers/settings-provider";
import { useNotification } from "@/providers/notification-provider";
import { Dialog } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import type { DocumentMetadata } from "@trustgraph/client";

// ---------------------------------------------------------------------------
// Upload dialog
// ---------------------------------------------------------------------------

function UploadDialog({
  open,
  onClose,
  onUpload,
}: {
  open: boolean;
  onClose: () => void;
  onUpload: (
    data: string,
    mimeType: string,
    title: string,
    comments: string,
    tags: string[],
  ) => Promise<void>;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [tags, setTags] = useState("");
  const [comments, setComments] = useState("");
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const reset = () => {
    setFile(null);
    setTitle("");
    setTags("");
    setComments("");
    setUploading(false);
  };

  const handleFile = (f: File) => {
    setFile(f);
    if (!title) setTitle(f.name.replace(/\.[^/.]+$/, ""));
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSubmit = async () => {
    if (!file) return;
    setUploading(true);
    try {
      const base64 = await fileToBase64(file);
      const tagList = tags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
      await onUpload(base64, file.type || "application/octet-stream", title, comments, tagList);
      reset();
      onClose();
    } catch {
      setUploading(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={() => {
        if (!uploading) {
          reset();
          onClose();
        }
      }}
      title="Upload Document"
      footer={
        <>
          <button
            onClick={() => {
              reset();
              onClose();
            }}
            disabled={uploading}
            className="rounded-lg border border-border px-4 py-2 text-sm text-fg-muted hover:bg-surface-200 disabled:opacity-40"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!file || !title.trim() || uploading}
            className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-500 disabled:opacity-40"
          >
            {uploading && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            Upload
          </button>
        </>
      }
    >
      {/* Drop zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={cn(
          "mb-4 flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-8 transition-colors",
          dragOver
            ? "border-brand-500 bg-brand-500/10"
            : "border-border hover:border-border-hover",
        )}
      >
        <Upload className="mb-2 h-8 w-8 text-fg-subtle" />
        {file ? (
          <div className="flex items-center gap-2 text-sm text-fg">
            <FileText className="h-4 w-4" />
            <span>{file.name}</span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setFile(null);
              }}
              className="ml-1 text-fg-subtle hover:text-fg"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        ) : (
          <>
            <p className="text-sm text-fg-muted">
              Drop a file here or click to browse
            </p>
            <p className="mt-1 text-xs text-fg-subtle">PDF, TXT, or other text formats</p>
          </>
        )}
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          accept=".pdf,.txt,.md,.csv,.json,.xml,.html"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) handleFile(f);
          }}
        />
      </div>

      {/* Title */}
      <div className="mb-3 space-y-1.5">
        <label className="block text-sm font-medium text-fg-muted">Title</label>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Document title"
          className="w-full rounded-lg border border-border bg-surface-100 px-3 py-2 text-sm text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        />
      </div>

      {/* Comments */}
      <div className="mb-3 space-y-1.5">
        <label className="block text-sm font-medium text-fg-muted">Comments</label>
        <input
          type="text"
          value={comments}
          onChange={(e) => setComments(e.target.value)}
          placeholder="Optional comments"
          className="w-full rounded-lg border border-border bg-surface-100 px-3 py-2 text-sm text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        />
      </div>

      {/* Tags */}
      <div className="space-y-1.5">
        <label className="block text-sm font-medium text-fg-muted">Tags</label>
        <input
          type="text"
          value={tags}
          onChange={(e) => setTags(e.target.value)}
          placeholder="Comma-separated tags"
          className="w-full rounded-lg border border-border bg-surface-100 px-3 py-2 text-sm text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        />
      </div>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Confirm delete dialog
// ---------------------------------------------------------------------------

function ConfirmDeleteDialog({
  open,
  docTitle,
  onClose,
  onConfirm,
}: {
  open: boolean;
  docTitle: string;
  onClose: () => void;
  onConfirm: () => void;
}) {
  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Delete Document"
      footer={
        <>
          <button
            onClick={onClose}
            className="rounded-lg border border-border px-4 py-2 text-sm text-fg-muted hover:bg-surface-200"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="rounded-lg bg-error px-4 py-2 text-sm font-medium text-white hover:opacity-90"
          >
            Delete
          </button>
        </>
      }
    >
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-error" />
        <p className="text-sm text-fg-muted">
          Are you sure you want to delete{" "}
          <span className="font-medium text-fg">{docTitle || "this document"}</span>?
          This action cannot be undone.
        </p>
      </div>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Library page
// ---------------------------------------------------------------------------

export default function LibraryPage() {
  const {
    documents,
    processing,
    loading,
    error,
    getDocuments,
    uploadDocument,
    removeDocument,
    getProcessing,
  } = useLibrary();
  const collection = useSettings((s) => s.settings.collection);
  const notify = useNotification();

  const [uploadOpen, setUploadOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<DocumentMetadata | null>(null);

  // Load documents and processing on mount
  useEffect(() => {
    getDocuments();
    getProcessing();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleUpload = async (
    data: string,
    mimeType: string,
    title: string,
    comments: string,
    tags: string[],
  ) => {
    try {
      await uploadDocument(data, mimeType, title, comments, tags);
      notify.success("Document uploaded", `"${title}" is being processed.`);
      getProcessing();
    } catch {
      notify.error("Upload failed", "Could not upload the document.");
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget?.id) return;
    try {
      await removeDocument(deleteTarget.id, collection);
      notify.success("Document deleted");
    } catch {
      notify.error("Delete failed");
    }
    setDeleteTarget(null);
  };

  const handleRefresh = () => {
    getDocuments();
    getProcessing();
  };

  const guessKind = (doc: DocumentMetadata): string => {
    const kind = doc.kind ?? doc["document-type"] ?? "";
    if (kind.includes("pdf")) return "PDF";
    if (kind.includes("text") || kind.includes("plain")) return "Text";
    if (kind.includes("html")) return "HTML";
    if (kind.includes("json")) return "JSON";
    return kind || "--";
  };

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <LibraryBig className="h-6 w-6 text-brand-400" />
          <h1 className="text-2xl font-bold text-fg">Library</h1>
          <span className="ml-2 rounded bg-surface-200 px-2 py-0.5 text-xs text-fg-subtle">
            {collection}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-sm text-fg-muted transition-colors hover:bg-surface-200 disabled:opacity-40"
          >
            <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
            Refresh
          </button>
          <button
            onClick={() => setUploadOpen(true)}
            className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-500"
          >
            <Upload className="h-4 w-4" />
            Upload
          </button>
        </div>
      </div>

      {/* Processing status */}
      {processing.length > 0 && (
        <div className="mb-4 rounded-lg border border-brand-500/30 bg-brand-500/5 p-3">
          <div className="mb-2 flex items-center gap-2 text-sm font-medium text-brand-300">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Processing ({processing.length})
          </div>
          <div className="space-y-1">
            {processing.map((p) => (
              <div key={p.id} className="flex items-center gap-2 text-xs text-fg-muted">
                <FileType2 className="h-3 w-3" />
                <span className="truncate">{p["document-id"] || p.id}</span>
                <Badge variant="info" className="ml-auto">
                  {p.flow || "processing"}
                </Badge>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Content */}
      {loading && documents.length === 0 && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="mr-2 h-5 w-5 animate-spin text-fg-subtle" />
          <span className="text-fg-subtle">Loading documents...</span>
        </div>
      )}

      {error && (
        <p className="py-8 text-center text-error">Error: {error}</p>
      )}

      {!loading && !error && documents.length === 0 && (
        <div className="flex flex-1 flex-col items-center justify-center">
          <LibraryBig className="mb-3 h-10 w-10 text-fg-subtle opacity-30" />
          <p className="text-fg-subtle">
            No documents yet. Upload one to get started.
          </p>
        </div>
      )}

      {documents.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border bg-surface-100 text-fg-muted">
              <tr>
                <th className="px-4 py-3 font-medium">Title</th>
                <th className="px-4 py-3 font-medium">Type</th>
                <th className="px-4 py-3 font-medium">Tags</th>
                <th className="px-4 py-3 font-medium">ID</th>
                <th className="px-4 py-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {documents.map((doc) => (
                <tr key={doc.id} className="hover:bg-surface-100/50">
                  <td className="px-4 py-3 text-fg">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 shrink-0 text-fg-subtle" />
                      {doc.title || "Untitled"}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant="default">{guessKind(doc)}</Badge>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {(doc.tags ?? []).map((tag) => (
                        <Badge key={tag} variant="info">{tag}</Badge>
                      ))}
                      {(!doc.tags || doc.tags.length === 0) && (
                        <span className="text-fg-subtle">--</span>
                      )}
                    </div>
                  </td>
                  <td className="max-w-[12rem] truncate px-4 py-3 font-mono text-xs text-fg-subtle">
                    {doc.id}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => setDeleteTarget(doc)}
                      className="rounded p-1.5 text-fg-subtle hover:bg-error/10 hover:text-error"
                      title="Delete document"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Dialogs */}
      <UploadDialog
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onUpload={handleUpload}
      />

      <ConfirmDeleteDialog
        open={deleteTarget != null}
        docTitle={deleteTarget?.title ?? deleteTarget?.id ?? ""}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      // Strip the data URL prefix (e.g. "data:application/pdf;base64,")
      const base64 = result.includes(",") ? result.split(",")[1]! : result;
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}
