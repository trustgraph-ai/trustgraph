import { useAtom, useAtomRefresh, useAtomSet, useAtomValue } from "@effect/atom-react";
import {
  BrainCircuit,
  Loader2,
  RefreshCw,
  Download,
  Trash2,
  AlertTriangle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  activeActionAtom,
  deleteKgCoreAtom,
  kgCoresAtom,
  knowledgeDeleteTargetAtom,
  loadKgCoreAtom,
  resultData,
  resultError,
  resultLoading,
} from "@/atoms/workbench";
import { Dialog } from "@/components/ui/dialog";

function DeleteCoreDialog({
  coreId,
  onClose,
  onConfirm,
}: {
  coreId: string | null;
  onClose: () => void;
  onConfirm: () => void;
}) {
  return (
    <Dialog
      open={coreId !== null}
      onClose={onClose}
      title="Delete Knowledge Core"
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
          Are you sure you want to delete knowledge core{" "}
          <span className="font-mono font-medium text-fg">{coreId ?? ""}</span>?
          This action cannot be undone.
        </p>
      </div>
    </Dialog>
  );
}

export default function KnowledgeCoresPage() {
  const result = useAtomValue(kgCoresAtom);
  const refresh = useAtomRefresh(kgCoresAtom);
  const loadCore = useAtomSet(loadKgCoreAtom);
  const deleteCore = useAtomSet(deleteKgCoreAtom);
  const [deleteTarget, setDeleteTarget] = useAtom(knowledgeDeleteTargetAtom);
  const actionInProgress = useAtomValue(activeActionAtom);

  const cores = resultData(result, []);
  const loading = resultLoading(result, cores);
  const error = resultError(result);

  return (
    <div className="flex h-full flex-col">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <BrainCircuit className="h-6 w-6 text-brand-400" />
          <h1 className="text-2xl font-bold text-fg">Knowledge Cores</h1>
          {!loading && (
            <span className="ml-2 rounded bg-surface-200 px-2 py-0.5 text-xs text-fg-muted">
              {cores.length} core{cores.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>

        <button
          onClick={refresh}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-sm text-fg-muted transition-colors hover:bg-surface-200 disabled:opacity-40"
        >
          <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
          Refresh
        </button>
      </div>

      {loading && cores.length === 0 && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="mr-2 h-5 w-5 animate-spin text-fg-subtle" />
          <span className="text-fg-subtle">Loading knowledge cores...</span>
        </div>
      )}

      {error !== null && (
        <p className="mb-4 rounded-lg bg-error/10 px-4 py-2 text-sm text-error">
          {error}
        </p>
      )}

      {!loading && error === null && cores.length === 0 && (
        <div className="flex flex-1 flex-col items-center justify-center">
          <BrainCircuit className="mb-3 h-10 w-10 text-fg-subtle opacity-30" />
          <p className="text-fg-subtle">No knowledge cores available.</p>
        </div>
      )}

      {cores.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border bg-surface-100 text-fg-muted">
              <tr>
                <th className="px-4 py-3 font-medium">Core ID</th>
                <th className="px-4 py-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {cores.map((id) => (
                <tr key={id} className="hover:bg-surface-100/50">
                  <td className="px-4 py-3">
                    <span className="font-mono text-sm text-fg">{id}</span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => loadCore(id)}
                        disabled={actionInProgress === id}
                        className="flex items-center gap-1.5 rounded px-2.5 py-1.5 text-xs font-medium text-brand-400 hover:bg-brand-600/10 disabled:opacity-40"
                        title="Load core"
                        aria-label={`Load core ${id}`}
                      >
                        {actionInProgress === id ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <Download className="h-3.5 w-3.5" />
                        )}
                        Load
                      </button>
                      <button
                        onClick={() => setDeleteTarget(id)}
                        disabled={actionInProgress === id}
                        className="flex items-center gap-1.5 rounded px-2.5 py-1.5 text-xs font-medium text-error hover:bg-error/10 disabled:opacity-40"
                        title="Delete core"
                        aria-label={`Delete core ${id}`}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <DeleteCoreDialog
        coreId={deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => {
          if (deleteTarget !== null) deleteCore(deleteTarget);
          setDeleteTarget(null);
        }}
      />
    </div>
  );
}
