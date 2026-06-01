import { useAtom, useAtomRefresh, useAtomSet, useAtomValue } from "@effect/atom-react";
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
import {
  documentMetadataAtom,
  encodeJsonUnknownString,
  libraryDeleteTargetAtom,
  libraryDetailTargetAtom,
  libraryDocumentsAtom,
  libraryProcessingAtom,
  librarySearchAtom,
  removeDocumentAtom,
  resultData,
  resultError,
  resultLoading,
  submitUploadDocumentAtom,
  uploadDialogOpenAtom,
  uploadFormAtom,
  type UploadForm,
} from "@/atoms/workbench";
import { Dialog } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import type { DocumentMetadata } from "@trustgraph/client";

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function guessKind(doc: DocumentMetadata): string {
  const kind = doc.kind ?? doc["document-type"] ?? "";
  if (kind.includes("pdf")) return "PDF";
  if (kind.includes("text") || kind.includes("plain")) return "Text";
  if (kind.includes("html")) return "HTML";
  if (kind.includes("json")) return "JSON";
  return kind.length > 0 ? kind : "--";
}

function resetUploadForm(form: UploadForm): UploadForm {
  return { ...form, file: null, title: "", tags: "", comments: "", uploading: false, dragOver: false, progress: null };
}

function UploadDialog() {
  const [open, setOpen] = useAtom(uploadDialogOpenAtom);
  const [form, setForm] = useAtom(uploadFormAtom);
  const submitUploadDocument = useAtomSet(submitUploadDocumentAtom);

  const progressPercent = form.progress !== null
    ? Math.round((form.progress.chunksUploaded / Math.max(form.progress.chunksTotal, 1)) * 100)
    : 0;

  const close = () => {
    if (!form.uploading) {
      setForm(resetUploadForm(form));
      setOpen(false);
    }
  };

  const submit = () => {
    submitUploadDocument(undefined);
  };

  return (
    <Dialog
      open={open}
      onClose={close}
      title="Upload Document"
      footer={
        <>
          <button
            onClick={close}
            disabled={form.uploading}
            className="rounded-lg border border-border px-4 py-2 text-sm text-fg-muted hover:bg-surface-200 disabled:opacity-40"
          >
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={form.file === null || form.title.trim().length === 0 || form.uploading}
            className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-500 disabled:opacity-40"
          >
            {form.uploading && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            Upload
          </button>
        </>
      }
    >
      <label
        onDragOver={(event) => {
          event.preventDefault();
          setForm({ ...form, dragOver: true });
        }}
        onDragLeave={() => setForm({ ...form, dragOver: false })}
        onDrop={(event) => {
          event.preventDefault();
          const file = event.dataTransfer.files[0];
          if (file !== undefined) {
            setForm({ ...form, file, title: form.title.length === 0 ? file.name.replace(/\.[^/.]+$/, "") : form.title, dragOver: false });
          }
        }}
        className={cn(
          "mb-4 flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-8 transition-colors",
          form.dragOver ? "border-brand-500 bg-brand-500/10" : "border-border hover:border-border-hover",
        )}
      >
        <Upload className="mb-2 h-8 w-8 text-fg-subtle" />
        {form.file !== null ? (
          <div className="flex items-center gap-2 text-sm text-fg">
            <FileText className="h-4 w-4" />
            <span>{form.file.name}</span>
            <span className="text-xs text-fg-subtle">({formatBytes(form.file.size)})</span>
            <button
              type="button"
              onClick={(event) => {
                event.preventDefault();
                setForm({ ...form, file: null, title: "" });
              }}
              aria-label="Remove selected file"
              className="ml-1 text-fg-subtle hover:text-fg"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        ) : (
          <>
            <p className="text-sm text-fg-muted">Drop a file here or click to browse</p>
            <p className="mt-1 text-xs text-fg-subtle">PDF, TXT, Markdown, CSV, JSON, XML, or HTML</p>
          </>
        )}
        <input
          type="file"
          className="hidden"
          accept=".pdf,.txt,.md,.csv,.json,.xml,.html"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file !== undefined) {
              setForm({ ...form, file, title: form.title.length === 0 ? file.name.replace(/\.[^/.]+$/, "") : form.title });
            }
          }}
        />
      </label>

      {form.uploading && form.progress !== null && (
        <div className="mb-4 space-y-1.5">
          <div className="flex items-center justify-between text-xs text-fg-muted">
            <span>
              {form.progress.phase === "preparing"
                ? "Preparing upload..."
                : form.progress.phase === "finalizing"
                  ? "Finalizing..."
                  : `Uploading chunk ${form.progress.chunksUploaded}/${form.progress.chunksTotal}`}
            </span>
            <span>{progressPercent}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-surface-200">
            <div className="h-full rounded-full bg-brand-500 transition-all duration-300" style={{ width: `${progressPercent}%` }} />
          </div>
        </div>
      )}

      {[
        ["title", "Title", "Document title"] as const,
        ["comments", "Comments", "Optional comments"] as const,
        ["tags", "Tags", "Comma-separated tags"] as const,
      ].map(([key, label, placeholder]) => (
        <label key={key} className="mb-3 block space-y-1.5">
          <span className="block text-sm font-medium text-fg-muted">{label}</span>
          <input
            value={form[key]}
            onChange={(event) => setForm({ ...form, [key]: event.target.value })}
            placeholder={placeholder}
            className="w-full rounded-lg border border-border bg-surface-100 px-3 py-2 text-sm text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </label>
      ))}
    </Dialog>
  );
}

function DocumentDetailDialog() {
  const [target, setTarget] = useAtom(libraryDetailTargetAtom);
  const result = useAtomValue(documentMetadataAtom(target?.id ?? ""));
  const full = resultData(result, null);
  const doc = full ?? target;
  const loading = target !== null && resultLoading(result, full);

  if (doc === null) return null;

  return (
    <Dialog open={target !== null} onClose={() => setTarget(null)} title="Document Details" className="max-w-xl">
      {loading && (
        <div className="mb-3 flex items-center gap-2 text-xs text-fg-subtle">
          <Loader2 className="h-3 w-3 animate-spin" />
          Loading full metadata...
        </div>
      )}
      <div className="space-y-4">
        <div>
          <h3 className="mb-1 text-xs font-medium uppercase tracking-wider text-fg-subtle">Title</h3>
          <p className="text-sm text-fg">{(doc.title ?? "").length > 0 ? doc.title : "Untitled"}</p>
        </div>
        <div>
          <h3 className="mb-1 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wider text-fg-subtle">
            <Hash className="h-3 w-3" /> Document ID
          </h3>
          <p className="break-all font-mono text-xs text-fg-muted">{doc.id}</p>
        </div>
        <div>
          <h3 className="mb-1 text-xs font-medium uppercase tracking-wider text-fg-subtle">Type</h3>
          <Badge>{doc.kind ?? doc["document-type"] ?? "--"}</Badge>
        </div>
        {(doc.comments ?? "").length > 0 && <p className="text-sm text-fg-muted">{doc.comments}</p>}
        {(doc.tags ?? []).length > 0 && (
          <div>
            <h3 className="mb-1 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wider text-fg-subtle">
              <Tag className="h-3 w-3" /> Tags
            </h3>
            <div className="flex flex-wrap gap-1.5">
              {(doc.tags ?? []).map((tag) => <Badge key={tag} variant="info">{tag}</Badge>)}
            </div>
          </div>
        )}
        {doc.time != null && (
          <div>
            <h3 className="mb-1 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wider text-fg-subtle">
              <Clock className="h-3 w-3" /> Created
            </h3>
            <p className="text-sm text-fg-muted">{new Date(doc.time * 1000).toLocaleString()}</p>
          </div>
        )}
        {doc.metadata !== undefined && doc.metadata.length > 0 && (
          <pre className="max-h-40 overflow-y-auto rounded-lg bg-surface-100 p-3 font-mono text-[10px] text-fg-muted">
            {encodeJsonUnknownString(doc.metadata)}
          </pre>
        )}
      </div>
    </Dialog>
  );
}

export default function LibraryPage() {
  const documentsResult = useAtomValue(libraryDocumentsAtom);
  const processingResult = useAtomValue(libraryProcessingAtom);
  const refreshDocuments = useAtomRefresh(libraryDocumentsAtom);
  const refreshProcessing = useAtomRefresh(libraryProcessingAtom);
  const [uploadOpen, setUploadOpen] = useAtom(uploadDialogOpenAtom);
  const [deleteTarget, setDeleteTarget] = useAtom(libraryDeleteTargetAtom);
  const setDetailTarget = useAtomSet(libraryDetailTargetAtom);
  const [searchTerm, setSearchTerm] = useAtom(librarySearchAtom);
  const removeDocument = useAtomSet(removeDocumentAtom);

  const documents = resultData(documentsResult, []);
  const processing = resultData(processingResult, []);
  const loading = resultLoading(documentsResult, documents);
  const error = resultError(documentsResult);
  const searchLower = searchTerm.toLowerCase();
  const filteredDocuments = searchLower.length === 0
    ? documents
    : documents.filter((doc) => {
        const title = (doc.title ?? "").toLowerCase();
        const id = (doc.id ?? "").toLowerCase();
        const tags = (doc.tags ?? []).join(" ").toLowerCase();
        return title.includes(searchLower) || id.includes(searchLower) || tags.includes(searchLower);
      });

  const refresh = () => {
    refreshDocuments();
    refreshProcessing();
  };

  return (
    <div className="flex h-full flex-col">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <LibraryBig className="h-6 w-6 text-brand-400" />
          <h1 className="text-2xl font-bold text-fg">Library</h1>
          {!loading && <Badge>{documents.length} document{documents.length !== 1 ? "s" : ""}</Badge>}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={refresh}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-sm text-fg-muted transition-colors hover:bg-surface-200 disabled:opacity-40"
          >
            <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
            Refresh
          </button>
          <button
            onClick={() => setUploadOpen(!uploadOpen)}
            className="flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-500"
          >
            <Upload className="h-3.5 w-3.5" />
            Upload
          </button>
        </div>
      </div>

      {processing.length > 0 && (
        <div className="mb-4 rounded-lg border border-brand-500/30 bg-brand-500/5 px-4 py-3">
          <div className="mb-2 flex items-center gap-2 text-sm font-medium text-brand-300">
            <Loader2 className="h-4 w-4 animate-spin" />
            Processing ({processing.length})
          </div>
          <div className="flex flex-wrap gap-2">
            {processing.map((item) => (
              <Badge key={item.id} variant="info">{item["document-id"] ?? item.id}</Badge>
            ))}
          </div>
        </div>
      )}

      <div className="mb-4 flex items-center gap-2 rounded-lg border border-border bg-surface-100 px-3 py-2">
        <Search className="h-4 w-4 text-fg-subtle" />
        <input
          value={searchTerm}
          onChange={(event) => setSearchTerm(event.target.value)}
          placeholder="Search documents..."
          className="min-w-0 flex-1 bg-transparent text-sm text-fg placeholder:text-fg-subtle focus:outline-none"
        />
      </div>

      {loading && documents.length === 0 && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="mr-2 h-5 w-5 animate-spin text-fg-subtle" />
          <span className="text-fg-subtle">Loading documents...</span>
        </div>
      )}

      {error !== null && (
        <p className="mb-4 rounded-lg bg-error/10 px-4 py-2 text-sm text-error">{error}</p>
      )}

      {!loading && filteredDocuments.length === 0 && (
        <div className="flex flex-1 flex-col items-center justify-center">
          <FileText className="mb-3 h-10 w-10 text-fg-subtle opacity-30" />
          <p className="text-fg-subtle">{documents.length === 0 ? "No documents uploaded yet." : "No documents match your search."}</p>
        </div>
      )}

      {filteredDocuments.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border bg-surface-100 text-fg-muted">
              <tr>
                <th className="px-4 py-3 font-medium">Title</th>
                <th className="px-4 py-3 font-medium">Type</th>
                <th className="px-4 py-3 font-medium">Tags</th>
                <th className="px-4 py-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filteredDocuments.map((doc) => {
                const id = doc.id ?? "";
                return (
                  <tr key={id} className="hover:bg-surface-100/50">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <FileType2 className="h-4 w-4 text-fg-subtle" />
                        <div className="min-w-0">
                          <p className="truncate font-medium text-fg">{doc.title ?? "Untitled"}</p>
                          <p className="truncate font-mono text-[10px] text-fg-subtle">{id}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3"><Badge>{guessKind(doc)}</Badge></td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {(doc.tags ?? []).slice(0, 4).map((tag) => <Badge key={tag} variant="info">{tag}</Badge>)}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex justify-end gap-1">
                        <button
                          onClick={() => setDetailTarget(doc)}
                          className="rounded p-1.5 text-fg-subtle hover:bg-surface-200 hover:text-fg"
                          aria-label={`View ${doc.title ?? id}`}
                        >
                          <Eye className="h-3.5 w-3.5" />
                        </button>
                        <button
                          onClick={() => setDeleteTarget(doc)}
                          className="rounded p-1.5 text-fg-subtle hover:bg-error/10 hover:text-error"
                          aria-label={`Delete ${doc.title ?? id}`}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <UploadDialog />
      <DocumentDetailDialog />
      <Dialog
        open={deleteTarget !== null}
        onClose={() => setDeleteTarget(null)}
        title="Delete Document"
        footer={
          <>
            <button
              onClick={() => setDeleteTarget(null)}
              className="rounded-lg border border-border px-4 py-2 text-sm text-fg-muted hover:bg-surface-200"
            >
              Cancel
            </button>
            <button
              onClick={() => {
                const id = deleteTarget?.id ?? "";
                if (id.length > 0) removeDocument(id);
                setDeleteTarget(null);
              }}
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
            Delete <span className="font-medium text-fg">{deleteTarget?.title ?? "this document"}</span>?
          </p>
        </div>
      </Dialog>
    </div>
  );
}
