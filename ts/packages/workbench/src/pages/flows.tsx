import { useCallback, useEffect, useState } from "react";
import {
  Workflow,
  Plus,
  Square,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  Loader2,
  AlertTriangle,
  Info,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useFlows, type FlowSummary } from "@/hooks/use-flows";
import { useSocket } from "@/providers/socket-provider";
import { useNotification } from "@/providers/notification-provider";
import { Dialog } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";

// ---------------------------------------------------------------------------
// Start flow dialog
// ---------------------------------------------------------------------------

function StartFlowDialog({
  open,
  onClose,
  onStart,
}: {
  open: boolean;
  onClose: () => void;
  onStart: (
    id: string,
    blueprint: string,
    description: string,
    params: Record<string, unknown>,
  ) => Promise<void>;
}) {
  const socket = useSocket();
  const [blueprints, setBlueprints] = useState<string[]>([]);
  const [loadingBlueprints, setLoadingBlueprints] = useState(false);
  const [id, setId] = useState("");
  const [blueprint, setBlueprint] = useState("");
  const [description, setDescription] = useState("");
  const [paramsJson, setParamsJson] = useState("{}");
  const [submitting, setSubmitting] = useState(false);
  const [paramsError, setParamsError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [blueprintDef, setBlueprintDef] = useState<Record<string, unknown> | null>(null);
  const [loadingDef, setLoadingDef] = useState(false);
  const [defExpanded, setDefExpanded] = useState(false);

  // Fetch blueprints when dialog opens
  useEffect(() => {
    if (!open) return;
    setLoadingBlueprints(true);
    socket
      .flows()
      .getFlowBlueprints()
      .then((names) => {
        const list = names ?? [];
        setBlueprints(list);
        if (list.length > 0 && !blueprint) {
          setBlueprint(list[0]!);
        }
      })
      .catch(() => setBlueprints([]))
      .finally(() => setLoadingBlueprints(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, socket]);

  // Fetch blueprint definition when selection changes
  useEffect(() => {
    if (!blueprint) {
      setBlueprintDef(null);
      return;
    }
    let cancelled = false;
    setLoadingDef(true);
    setBlueprintDef(null);
    socket
      .flows()
      .getFlowBlueprint(blueprint)
      .then((def) => {
        if (cancelled) return;
        setBlueprintDef(def);
        // Pre-populate parameters with defaults from the definition
        const paramsDef =
          def?.parameters ?? def?.params ?? def?.["parameters"] ?? def?.["params"];
        if (paramsDef && typeof paramsDef === "object") {
          const defaults: Record<string, unknown> = {};
          const params = paramsDef as Record<string, unknown>;
          for (const [key, val] of Object.entries(params)) {
            if (val && typeof val === "object" && "default" in (val as Record<string, unknown>)) {
              defaults[key] = (val as Record<string, unknown>).default;
            }
          }
          if (Object.keys(defaults).length > 0) {
            setParamsJson(JSON.stringify(defaults, null, 2));
          }
        }
      })
      .catch(() => {
        if (!cancelled) setBlueprintDef(null);
      })
      .finally(() => {
        if (!cancelled) setLoadingDef(false);
      });
    return () => {
      cancelled = true;
    };
  }, [blueprint, socket]);

  const reset = () => {
    setId("");
    setBlueprint("");
    setDescription("");
    setParamsJson("{}");
    setParamsError(null);
    setSubmitting(false);
    setSubmitted(false);
    setBlueprintDef(null);
    setLoadingDef(false);
    setDefExpanded(false);
  };

  const handleSubmit = async () => {
    setSubmitted(true);
    if (!isValid) return;

    let params: Record<string, unknown> = {};
    try {
      params = JSON.parse(paramsJson);
      setParamsError(null);
    } catch {
      setParamsError("Invalid JSON");
      return;
    }

    setSubmitting(true);
    try {
      await onStart(id, blueprint, description, params);
      reset();
      onClose();
    } catch {
      setSubmitting(false);
    }
  };

  const isValid = id.trim().length > 0 && blueprint.length > 0 && description.trim().length > 0;

  return (
    <Dialog
      open={open}
      onClose={() => {
        if (!submitting) {
          reset();
          onClose();
        }
      }}
      title="Start Flow"
      footer={
        <>
          <button
            onClick={() => {
              reset();
              onClose();
            }}
            disabled={submitting}
            className="rounded-lg border border-border px-4 py-2 text-sm text-fg-muted hover:bg-surface-200 disabled:opacity-40"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-500 disabled:opacity-40"
          >
            {submitting && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            <Plus className="h-3.5 w-3.5" />
            Start
          </button>
        </>
      }
    >
      {/* Flow ID */}
      <div className="mb-3 space-y-1.5">
        <label htmlFor="flow-id" className="block text-sm font-medium text-fg-muted">
          Flow ID <span className="text-error">*</span>
        </label>
        <input
          id="flow-id"
          type="text"
          value={id}
          onChange={(e) => setId(e.target.value)}
          placeholder="my-flow-id"
          className="w-full rounded-lg border border-border bg-surface-100 px-3 py-2 text-sm text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        />
        {submitted && !id.trim() && (
          <p className="mt-1 text-xs text-red-400">Flow ID is required</p>
        )}
      </div>

      {/* Blueprint name */}
      <div className="mb-3 space-y-1.5">
        <label htmlFor="flow-blueprint" className="block text-sm font-medium text-fg-muted">
          Blueprint <span className="text-error">*</span>
        </label>
        {loadingBlueprints ? (
          <div className="flex items-center gap-2 py-2 text-xs text-fg-subtle">
            <Loader2 className="h-3 w-3 animate-spin" /> Loading blueprints...
          </div>
        ) : (
          <select
            id="flow-blueprint"
            value={blueprint}
            onChange={(e) => setBlueprint(e.target.value)}
            className="w-full rounded-lg border border-border bg-surface-100 px-3 py-2 text-sm text-fg focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          >
            <option value="" disabled>
              Select a blueprint
            </option>
            {blueprints.map((bp) => (
              <option key={bp} value={bp}>
                {bp}
              </option>
            ))}
          </select>
        )}
        {submitted && !blueprint && (
          <p className="mt-1 text-xs text-red-400">Blueprint is required</p>
        )}

        {/* Blueprint details info section */}
        {loadingDef && (
          <div className="mt-2 flex items-center gap-2 text-xs text-fg-subtle">
            <Loader2 className="h-3 w-3 animate-spin" /> Loading blueprint details...
          </div>
        )}

        {blueprintDef && !loadingDef && (
          <div className="mt-2 rounded-lg border border-border bg-surface-50 p-3">
            <div className="flex items-center gap-1.5 text-xs font-medium text-fg-muted">
              <Info className="h-3.5 w-3.5 text-brand-400" />
              Blueprint Details
            </div>

            {/* Description from definition */}
            {!!(blueprintDef.description || blueprintDef.desc) && (
              <p className="mt-1.5 text-xs text-fg-muted">
                {String(blueprintDef.description ?? blueprintDef.desc)}
              </p>
            )}

            {/* Parameters schema */}
            {(() => {
              const paramsDef =
                blueprintDef.parameters ??
                blueprintDef.params ??
                blueprintDef["parameters"] ??
                blueprintDef["params"];
              if (!paramsDef || typeof paramsDef !== "object") return null;
              const entries = Object.entries(paramsDef as Record<string, unknown>);
              if (entries.length === 0) return null;
              return (
                <div className="mt-2">
                  <p className="text-xs font-medium text-fg-muted">Parameters</p>
                  <div className="mt-1 space-y-1">
                    {entries.map(([name, schema]) => {
                      const s = schema as Record<string, unknown> | null;
                      const type = s?.type ? String(s.type) : undefined;
                      const defaultVal = s && "default" in s ? s.default : undefined;
                      const desc = s?.description ? String(s.description) : undefined;
                      return (
                        <div
                          key={name}
                          className="flex flex-wrap items-baseline gap-x-2 text-xs"
                        >
                          <span className="font-mono font-medium text-fg">{name}</span>
                          {type && (
                            <span className="rounded bg-surface-200 px-1 py-0.5 text-[10px] text-fg-subtle">
                              {type}
                            </span>
                          )}
                          {defaultVal !== undefined && (
                            <span className="text-fg-subtle">
                              default: <span className="font-mono">{JSON.stringify(defaultVal)}</span>
                            </span>
                          )}
                          {desc && <span className="text-fg-subtle">- {desc}</span>}
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })()}

            {/* Raw JSON toggle */}
            <button
              type="button"
              onClick={() => setDefExpanded((p) => !p)}
              className="mt-2 flex items-center gap-1 text-[11px] text-fg-subtle hover:text-fg-muted"
            >
              {defExpanded ? (
                <ChevronDown className="h-3 w-3" />
              ) : (
                <ChevronRight className="h-3 w-3" />
              )}
              Raw definition
            </button>
            {defExpanded && (
              <pre className="mt-1 max-h-40 overflow-auto rounded border border-border bg-surface-100 p-2 font-mono text-[11px] text-fg-subtle">
                {JSON.stringify(blueprintDef, null, 2)}
              </pre>
            )}
          </div>
        )}
      </div>

      {/* Description */}
      <div className="mb-3 space-y-1.5">
        <label htmlFor="flow-description" className="block text-sm font-medium text-fg-muted">
          Description <span className="text-error">*</span>
        </label>
        <input
          id="flow-description"
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Human-readable description"
          className="w-full rounded-lg border border-border bg-surface-100 px-3 py-2 text-sm text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        />
        {submitted && !description.trim() && (
          <p className="mt-1 text-xs text-red-400">Description is required</p>
        )}
      </div>

      {/* Parameters (JSON) */}
      <div className="space-y-1.5">
        <label htmlFor="flow-params" className="block text-sm font-medium text-fg-muted">
          Parameters (JSON)
        </label>
        <textarea
          id="flow-params"
          value={paramsJson}
          onChange={(e) => {
            setParamsJson(e.target.value);
            setParamsError(null);
          }}
          rows={4}
          className={cn(
            "w-full resize-none rounded-lg border bg-surface-100 px-3 py-2 font-mono text-xs text-fg placeholder:text-fg-subtle focus:outline-none focus:ring-1",
            paramsError
              ? "border-error focus:border-error focus:ring-error"
              : "border-border focus:border-brand-500 focus:ring-brand-500",
          )}
        />
        {paramsError && (
          <p className="text-xs text-error">{paramsError}</p>
        )}
      </div>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Stop flow confirm dialog
// ---------------------------------------------------------------------------

function StopFlowDialog({
  open,
  flowId,
  onClose,
  onConfirm,
}: {
  open: boolean;
  flowId: string;
  onClose: () => void;
  onConfirm: () => Promise<void>;
}) {
  const [stopping, setStopping] = useState(false);

  const handleStop = async () => {
    setStopping(true);
    try {
      await onConfirm();
    } finally {
      setStopping(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={() => {
        if (!stopping) onClose();
      }}
      title="Stop Flow"
      footer={
        <>
          <button
            onClick={onClose}
            disabled={stopping}
            className="rounded-lg border border-border px-4 py-2 text-sm text-fg-muted hover:bg-surface-200 disabled:opacity-40"
          >
            Cancel
          </button>
          <button
            onClick={handleStop}
            disabled={stopping}
            className="flex items-center gap-2 rounded-lg bg-error px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-40"
          >
            {stopping && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            Stop
          </button>
        </>
      }
    >
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-error" />
        <p className="text-sm text-fg-muted">
          Are you sure you want to stop flow{" "}
          <span className="font-mono font-medium text-fg">{flowId}</span>?
        </p>
      </div>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Flow detail row (expandable)
// ---------------------------------------------------------------------------

function FlowRow({
  flow,
  onStop,
}: {
  flow: FlowSummary;
  onStop: (id: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);

  // Determine all the extra keys beyond id/description
  const detailKeys = Object.keys(flow).filter(
    (k) => k !== "id" && k !== "description",
  );

  return (
    <>
      <tr
        className="cursor-pointer hover:bg-surface-100/50"
        onClick={() => setExpanded((p) => !p)}
      >
        <td className="px-4 py-3">
          <div className="flex items-center gap-2">
            {expanded ? (
              <ChevronDown className="h-3.5 w-3.5 shrink-0 text-fg-subtle" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5 shrink-0 text-fg-subtle" />
            )}
            <span className="font-mono text-sm text-fg">{flow.id}</span>
          </div>
        </td>
        <td className="px-4 py-3 text-fg-muted">
          {flow.description || "--"}
        </td>
        <td className="px-4 py-3">
          <Badge variant="success">Running</Badge>
        </td>
        <td className="px-4 py-3 text-right">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onStop(flow.id);
            }}
            className="rounded p-1.5 text-fg-subtle hover:bg-error/10 hover:text-error"
            title="Stop flow"
            aria-label={`Stop flow ${flow.id}`}
          >
            <Square className="h-3.5 w-3.5" />
          </button>
        </td>
      </tr>

      {/* Detail row */}
      {expanded && detailKeys.length > 0 && (
        <tr>
          <td colSpan={4} className="bg-surface-50 px-8 py-3">
            <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-xs">
              {detailKeys.map((key) => (
                <div key={key}>
                  <span className="font-medium text-fg-muted">{key}: </span>
                  <span className="text-fg-subtle">
                    {typeof flow[key] === "object"
                      ? JSON.stringify(flow[key])
                      : String(flow[key] ?? "")}
                  </span>
                </div>
              ))}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Flows page
// ---------------------------------------------------------------------------

export default function FlowsPage() {
  const { flows, loading, error, getFlows, startFlow, stopFlow } = useFlows();
  const notify = useNotification();

  const [createOpen, setCreateOpen] = useState(false);
  const [stopTarget, setStopTarget] = useState<string | null>(null);

  // Auto-refresh every 10 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      getFlows();
    }, 10_000);
    return () => clearInterval(interval);
  }, [getFlows]);

  // Also refresh on window focus
  useEffect(() => {
    const handler = () => getFlows();
    window.addEventListener("focus", handler);
    return () => window.removeEventListener("focus", handler);
  }, [getFlows]);

  const handleStart = async (
    id: string,
    blueprint: string,
    description: string,
    params: Record<string, unknown>,
  ) => {
    try {
      await startFlow(id, blueprint, description, params);
      notify.success("Flow started", `Flow "${id}" has been started.`);
    } catch (err) {
      notify.error(
        "Failed to start flow",
        err instanceof Error ? err.message : String(err),
      );
      throw err; // re-throw so dialog stays open
    }
  };

  const handleStop = async () => {
    if (!stopTarget) return;
    try {
      await stopFlow(stopTarget);
      notify.success("Flow stopped", `Flow "${stopTarget}" has been stopped.`);
    } catch (err) {
      notify.error(
        "Failed to stop flow",
        err instanceof Error ? err.message : String(err),
      );
    }
    setStopTarget(null);
  };

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <Workflow className="h-6 w-6 text-brand-400" />
          <h1 className="text-2xl font-bold text-fg">Flows</h1>
          <span className="ml-2 rounded bg-surface-200 px-2 py-0.5 text-xs text-fg-muted">
            {flows.length} active
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => getFlows()}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-sm text-fg-muted transition-colors hover:bg-surface-200 disabled:opacity-40"
          >
            <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
            Refresh
          </button>
          <button
            onClick={() => setCreateOpen(true)}
            className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-500"
          >
            <Plus className="h-4 w-4" />
            Start Flow
          </button>
        </div>
      </div>

      {/* Content */}
      {loading && flows.length === 0 && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="mr-2 h-5 w-5 animate-spin text-fg-subtle" />
          <span className="text-fg-subtle">Loading flows...</span>
        </div>
      )}

      {error && (
        <p role="alert" className="mb-4 rounded-lg bg-error/10 px-4 py-2 text-sm text-error">
          {error}
        </p>
      )}

      {!loading && !error && flows.length === 0 && (
        <div className="flex flex-1 flex-col items-center justify-center">
          <Workflow className="mb-3 h-10 w-10 text-fg-subtle opacity-30" />
          <p className="text-fg-subtle">No flows configured.</p>
          <p className="mt-1 text-xs text-fg-subtle">
            Click "Start Flow" to create one.
          </p>
        </div>
      )}

      {flows.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border bg-surface-100 text-fg-muted">
              <tr>
                <th className="px-4 py-3 font-medium">ID</th>
                <th className="px-4 py-3 font-medium">Description</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {flows.map((flow) => (
                <FlowRow
                  key={flow.id}
                  flow={flow}
                  onStop={(id) => setStopTarget(id)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Dialogs */}
      <StartFlowDialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onStart={handleStart}
      />

      <StopFlowDialog
        open={stopTarget != null}
        flowId={stopTarget ?? ""}
        onClose={() => setStopTarget(null)}
        onConfirm={handleStop}
      />
    </div>
  );
}
