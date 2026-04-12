import { useCallback, useEffect, useState } from "react";
import {
  BrainCircuit,
  Loader2,
  RefreshCw,
  Download,
  Trash2,
  AlertTriangle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useSocket } from "@/providers/socket-provider";
import { useConnectionState } from "@/providers/socket-provider";
import { useNotification } from "@/providers/notification-provider";
import { useSessionStore } from "@/hooks/use-session-store";
import { Dialog } from "@/components/ui/dialog";

// ---------------------------------------------------------------------------
// Delete confirmation dialog
// ---------------------------------------------------------------------------

function DeleteCoreDialog({
  open,
  coreId,
  onClose,
  onConfirm,
}: {
  open: boolean;
  coreId: string;
  onClose: () => void;
  onConfirm: () => void;
}) {
  return (
    <Dialog
      open={open}
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
          <span className="font-mono font-medium text-fg">{coreId}</span>?
          This action cannot be undone.
        </p>
      </div>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Knowledge Cores page
// ---------------------------------------------------------------------------

export default function KnowledgeCoresPage() {
  const socket = useSocket();
  const connectionState = useConnectionState();
  const notify = useNotification();
  const flowId = useSessionStore((s) => s.flowId);

  const [cores, setCores] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);

  const loadCores = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const timeoutPromise = new Promise<never>((_, reject) =>
        setTimeout(() => reject(new Error("Request timed out")), 15000),
      );
      const ids = await Promise.race([
        socket.knowledge().getKnowledgeCores(),
        timeoutPromise,
      ]);
      setCores(Array.isArray(ids) ? ids : []);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
      console.error("Failed to load knowledge cores:", err);
    } finally {
      setLoading(false);
    }
  }, [socket]);

  // Auto-load when connected
  useEffect(() => {
    const connected =
      connectionState.status === "connected" ||
      connectionState.status === "authenticated" ||
      connectionState.status === "unauthenticated";
    if (connected) {
      loadCores();
    }
  }, [connectionState.status, loadCores]);

  const handleLoad = useCallback(
    async (id: string) => {
      setActionInProgress(id);
      try {
        await socket.knowledge().loadKgCore(id, flowId);
        notify.success("Core loaded", `Knowledge core "${id}" has been loaded.`);
      } catch (err) {
        notify.error(
          "Failed to load core",
          err instanceof Error ? err.message : String(err),
        );
      } finally {
        setActionInProgress(null);
      }
    },
    [socket, flowId, notify],
  );

  const handleDelete = useCallback(async () => {
    if (!deleteTarget) return;
    setActionInProgress(deleteTarget);
    try {
      await socket.knowledge().deleteKgCore(deleteTarget);
      notify.success("Core deleted", `Knowledge core "${deleteTarget}" has been deleted.`);
      await loadCores();
    } catch (err) {
      notify.error(
        "Failed to delete core",
        err instanceof Error ? err.message : String(err),
      );
    } finally {
      setActionInProgress(null);
      setDeleteTarget(null);
    }
  }, [socket, deleteTarget, notify, loadCores]);

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
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
          onClick={loadCores}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-sm text-fg-muted transition-colors hover:bg-surface-200 disabled:opacity-40"
        >
          <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
          Refresh
        </button>
      </div>

      {/* Content */}
      {loading && cores.length === 0 && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="mr-2 h-5 w-5 animate-spin text-fg-subtle" />
          <span className="text-fg-subtle">Loading knowledge cores...</span>
        </div>
      )}

      {error && (
        <p className="mb-4 rounded-lg bg-error/10 px-4 py-2 text-sm text-error">
          {error}
        </p>
      )}

      {!loading && !error && cores.length === 0 && (
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
                        onClick={() => handleLoad(id)}
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

      {/* Delete confirmation dialog */}
      <DeleteCoreDialog
        open={deleteTarget != null}
        coreId={deleteTarget ?? ""}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
      />
    </div>
  );
}
