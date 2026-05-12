import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
  Search,
  Eye,
  Clock,
  Tag,
  Hash,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useLibrary, type UploadProgress } from "@/hooks/use-library";
import { useSettings } from "@/providers/settings-provider";
import { useNotification } from "@/providers/notification-provider";
import { Dialog } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import type { DocumentMetadata } from "@trustgraph/client";

// Threshold for chunked upload (1 MB base64 ~ 750 KB raw)
const CHUNKED_UPLOAD_THRESHOLD = 1_000_000;

// ---------------------------------------------------------------------------
// Upload dialog
// ---------------------------------------------------------------------------

function UploadDialog({
  open,
  onClose,
  onUpload,
  onUploadChunked,
  onError,
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
  onUploadChunked: (
    data: string,
    mimeType: string,
    title: string,
    comments: string,
    tags: string[],
    onProgress: (progress: UploadProgress) => void,
  ) => Promise<void>;
  onError?: (msg: string) => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [tags, setTags] = useState("");
  const [comments, setComments] = useState("");
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [progress, setProgress] = useState<UploadProgress | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const reset = () => {
    setFile(null);
    setTitle("");
    setTags("");
    setComments("");
    setUploading(false);
    setProgress(null);
  };

  const titleRef = useRef(title);
  titleRef.current = title;

  const handleFile = useCallback((f: File) => {
    setFile(f);
    if (titleRef.current.length === 0) setTitle(f.name.replace(/\.[^/.]+$/, ""));
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f !== undefined) handleFile(f);
  }, [handleFile]);

  const handleSubmit = async () => {
    if (file === null) return;
    setUploading(true);
    try {
      const base64 = await fileToBase64(file);
      const tagList = tags
        .split(",")
        .map((t) => t.trim())
        .filter((tag) => tag.length > 0);
      const mimeType =
        file.type.length > 0 ? file.type : "application/octet-stream";

      if (base64.length > CHUNKED_UPLOAD_THRESHOLD) {
        await onUploadChunked(base64, mimeType, title, comments, tagList, setProgress);
      } else {
        await onUpload(base64, mimeType, title, comments, tagList);
      }
      reset();
      onClose();
    } catch (err) {
      onError?.(err instanceof Error ? err.message : "Upload failed");
      setUploading(false);
      setProgress(null);
    }
  };

  const progressPercent = progress
    !== null
    ? Math.round((progress.chunksUploaded / Math.max(progress.chunksTotal, 1)) * 100)
    : 0;

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
            disabled={file === null || title.trim().length === 0 || uploading}
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
        role="button"
        tabIndex={0}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
        aria-label="Drop a file here or press Enter to browse"
        className={cn(
          "mb-4 flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-8 transition-colors",
          dragOver
            ? "border-brand-500 bg-brand-500/10"
            : "border-border hover:border-border-hover",
        )}
      >
        <Upload className="mb-2 h-8 w-8 text-fg-subtle" />
        {file !== null ? (
          <div className="flex items-center gap-2 text-sm text-fg">
            <FileText className="h-4 w-4" />
            <span>{file.name}</span>
            <span className="text-xs text-fg-subtle">({formatBytes(file.size)})</span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setFile(null);
                setTitle("");
              }}
              aria-label="Remove selected file"
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
	            if (f !== undefined) handleFile(f);
	          }}
        />
      </div>

      {/* Upload progress bar */}
      {uploading && progress !== null && (
        <div className="mb-4 space-y-1.5">
          <div className="flex items-center justify-between text-xs text-fg-muted">
            <span>
              {progress.phase === "preparing"
                ? "Preparing upload..."
                : progress.phase === "finalizing"
                  ? "Finalizing..."
                  : `Uploading chunk ${progress.chunksUploaded}/${progress.chunksTotal}`}
            </span>
            <span>{progressPercent}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-surface-200">
            <div
              className="h-full rounded-full bg-brand-500 transition-all duration-300"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      )}

      {/* Title */}
      <div className="mb-3 space-y-1.5">
        <label htmlFor="upload-title" className="block text-sm font-medium text-fg-muted">Title</label>
        <input
          id="upload-title"
          type="text"
          required
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Document title"
          className="w-full rounded-lg border border-border bg-surface-100 px-3 py-2 text-sm text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        />
      </div>

      {/* Comments */}
      <div className="mb-3 space-y-1.5">
        <label htmlFor="upload-comments" className="block text-sm font-medium text-fg-muted">Comments</label>
        <input
          id="upload-comments"
          type="text"
          value={comments}
          onChange={(e) => setComments(e.target.value)}
          placeholder="Optional comments"
          className="w-full rounded-lg border border-border bg-surface-100 px-3 py-2 text-sm text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        />
      </div>

      {/* Tags */}
      <div className="space-y-1.5">
        <label htmlFor="upload-tags" className="block text-sm font-medium text-fg-muted">Tags</label>
        <input
          id="upload-tags"
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
// Document detail dialog
// ---------------------------------------------------------------------------

function DocumentDetailDialog({
  open,
  doc,
  loading: loadingMeta,
  onClose,
}: {
  open: boolean;
  doc: DocumentMetadata | null;
  loading?: boolean;
  onClose: () => void;
}) {
  if (doc === null) return null;

  return (
    <Dialog open={open} onClose={onClose} title="Document Details" className="max-w-xl">
      {loadingMeta === true && (
        <div className="mb-3 flex items-center gap-2 text-xs text-fg-subtle">
          <Loader2 className="h-3 w-3 animate-spin" />
          Loading full metadata...
        </div>
      )}
      <div className="space-y-4">
        {/* Title */}
        <div>
          <h3 className="mb-1 text-xs font-medium uppercase tracking-wider text-fg-subtle">Title</h3>
          <p className="text-sm text-fg">
            {(doc.title ?? "").length > 0 ? doc.title : "Untitled"}
          </p>
        </div>

        {/* ID */}
        <div>
          <h3 className="mb-1 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wider text-fg-subtle">
            <Hash className="h-3 w-3" /> Document ID
          </h3>
          <p className="break-all font-mono text-xs text-fg-muted">{doc.id}</p>
        </div>

        {/* Type */}
        <div>
          <h3 className="mb-1 text-xs font-medium uppercase tracking-wider text-fg-subtle">Type</h3>
          <Badge variant="default">{doc.kind ?? doc["document-type"] ?? "--"}</Badge>
        </div>

        {/* Comments */}
        {(doc.comments ?? "").length > 0 && (
          <div>
            <h3 className="mb-1 text-xs font-medium uppercase tracking-wider text-fg-subtle">Comments</h3>
            <p className="text-sm text-fg-muted">{doc.comments}</p>
          </div>
        )}

        {/* Tags */}
        {(doc.tags ?? []).length > 0 && (
          <div>
            <h3 className="mb-1 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wider text-fg-subtle">
              <Tag className="h-3 w-3" /> Tags
            </h3>
            <div className="flex flex-wrap gap-1.5">
              {(doc.tags ?? []).map((tag) => (
                <Badge key={tag} variant="info">{tag}</Badge>
              ))}
            </div>
          </div>
        )}

        {/* Timestamp */}
        {doc.time != null && (
          <div>
            <h3 className="mb-1 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wider text-fg-subtle">
              <Clock className="h-3 w-3" /> Created
            </h3>
            <p className="text-sm text-fg-muted">
              {new Date(doc.time * 1000).toLocaleString()}
            </p>
          </div>
        )}

        {/* User */}
        {(doc.user ?? "").length > 0 && (
          <div>
            <h3 className="mb-1 text-xs font-medium uppercase tracking-wider text-fg-subtle">Uploaded by</h3>
            <p className="text-sm text-fg-muted">{doc.user}</p>
          </div>
        )}

        {/* Raw metadata (if any RDF triples) */}
        {doc.metadata !== undefined && doc.metadata.length > 0 && (
          <div>
            <h3 className="mb-1 text-xs font-medium uppercase tracking-wider text-fg-subtle">
              Metadata ({doc.metadata.length} triples)
            </h3>
            <pre className="max-h-40 overflow-y-auto rounded-lg bg-surface-100 p-3 font-mono text-[10px] text-fg-muted">
              {JSON.stringify(doc.metadata, null, 2)}
            </pre>
          </div>
        )}
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
          <span className="font-medium text-fg">
            {docTitle.length > 0 ? docTitle : "this document"}
          </span>?
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
    uploadDocumentChunked,
    removeDocument,
    getProcessing,
    getDocumentMetadata,
  } = useLibrary();
  const collection = useSettings((s) => s.settings.collection);
  const notify = useNotification();

  const [uploadOpen, setUploadOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<DocumentMetadata | null>(null);
  const [detailDoc, setDetailDoc] = useState<DocumentMetadata | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");

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

  const handleUploadChunked = async (
    data: string,
    mimeType: string,
    title: string,
    comments: string,
    tags: string[],
    onProgress: (progress: UploadProgress) => void,
  ) => {
    try {
      await uploadDocumentChunked(data, mimeType, title, comments, tags, onProgress);
      notify.success("Document uploaded", `"${title}" is being processed.`);
      getProcessing();
    } catch {
      notify.error("Upload failed", "Could not upload the document.");
    }
  };

  const handleDelete = async () => {
    const target = deleteTarget;
    const targetId = target?.id ?? "";
    if (target === null || targetId.length === 0) {
      setDeleteTarget(null);
      return;
    }
    try {
      await removeDocument(targetId, collection);
      notify.success("Document deleted");
    } catch {
      notify.error("Delete failed");
    }
    setDeleteTarget(null);
  };

  const handleViewDetail = useCallback(
    async (doc: DocumentMetadata) => {
      setDetailDoc(doc);
      setDetailOpen(true);
      const id = doc.id ?? "";
      if (id.length > 0) {
        setLoadingDetail(true);
        const fullMeta = await getDocumentMetadata(id);
        if (fullMeta !== null) setDetailDoc(fullMeta);
        setLoadingDetail(false);
      }
    },
    [getDocumentMetadata],
  );

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
    return kind.length > 0 ? kind : "--";
  };

  // Search/filter
  const searchLower = searchTerm.toLowerCase();
  const filteredDocuments = useMemo(() => {
    if (searchLower.length === 0) return documents;
    return documents.filter((doc) => {
      const title = (doc.title ?? "").toLowerCase();
      const id = (doc.id ?? "").toLowerCase();
      const tags = (doc.tags ?? []).join(" ").toLowerCase();
      const kind = (doc.kind ?? doc["document-type"] ?? "").toLowerCase();
      return (
        title.includes(searchLower) ||
        id.includes(searchLower) ||
        tags.includes(searchLower) ||
        kind.includes(searchLower)
      );
    });
  }, [documents, searchLower]);

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <LibraryBig className="h-6 w-6 text-brand-400" />
          <h1 className="text-2xl font-bold text-fg">Library</h1>
          <span className="ml-2 rounded bg-surface-200 px-2 py-0.5 text-xs text-fg-muted">
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

      {/* Search bar */}
      {documents.length > 0 && (
        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-fg-subtle" />
          <input
            id="library-search"
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search by title, tags, type, or ID..."
            aria-label="Search documents"
            className="w-full rounded-lg border border-border bg-surface-100 py-2 pl-9 pr-9 text-sm text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
          {searchTerm.length > 0 && (
            <button
              onClick={() => setSearchTerm("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-fg-subtle hover:text-fg"
              aria-label="Clear search"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      )}

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
	                <span className="truncate">
	                  {(p["document-id"] ?? "").length > 0 ? p["document-id"] : p.id}
	                </span>
                <Badge variant="info" className="ml-auto">
	                  {p.flow.length > 0 ? p.flow : "processing"}
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

      {error !== null && (
        <p className="py-8 text-center text-error">Error: {error}</p>
      )}

      {!loading && error === null && documents.length === 0 && (
        <div className="flex flex-1 flex-col items-center justify-center">
          <LibraryBig className="mb-3 h-10 w-10 text-fg-subtle opacity-30" />
          <p className="text-fg-subtle">
            No documents yet. Upload one to get started.
          </p>
        </div>
      )}

      {/* Search results info */}
      {searchTerm.length > 0 && documents.length > 0 && (
        <p className="mb-2 text-xs text-fg-subtle">
          {filteredDocuments.length} of {documents.length} documents match
        </p>
      )}

      {filteredDocuments.length > 0 && (
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
              {filteredDocuments.map((doc, index) => (
                <tr key={doc.id ?? `${doc.title ?? "document"}-${index}`} className="hover:bg-surface-100/50">
                  <td className="px-4 py-3 text-fg">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 shrink-0 text-fg-subtle" />
	                      {(doc.title ?? "").length > 0 ? doc.title : "Untitled"}
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
	                      {(doc.tags ?? []).length === 0 && (
                        <span className="text-fg-subtle">--</span>
                      )}
                    </div>
                  </td>
                  <td className="max-w-[12rem] truncate px-4 py-3 font-mono text-xs text-fg-subtle">
                    {doc.id}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => handleViewDetail(doc)}
                        className="rounded p-1.5 text-fg-subtle hover:bg-surface-200 hover:text-fg"
                        title="View details"
                        aria-label="View document details"
                      >
                        <Eye className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={() => setDeleteTarget(doc)}
                        className="rounded p-1.5 text-fg-subtle hover:bg-error/10 hover:text-error"
                        title="Delete document"
                        aria-label="Delete document"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Empty search results */}
      {searchTerm.length > 0 && filteredDocuments.length === 0 && documents.length > 0 && (
        <div className="flex flex-1 flex-col items-center justify-center py-12">
          <Search className="mb-3 h-8 w-8 text-fg-subtle opacity-30" />
          <p className="text-fg-subtle">No documents match "{searchTerm}"</p>
        </div>
      )}

      {/* Dialogs */}
      <UploadDialog
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onUpload={handleUpload}
        onUploadChunked={handleUploadChunked}
        onError={(msg) => notify.error("Upload failed", msg)}
      />

      <ConfirmDeleteDialog
        open={deleteTarget !== null}
        docTitle={deleteTarget?.title ?? deleteTarget?.id ?? ""}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
      />

      <DocumentDetailDialog
        open={detailOpen}
        doc={detailDoc}
        loading={loadingDetail}
        onClose={() => {
          setDetailOpen(false);
          setDetailDoc(null);
        }}
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

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
