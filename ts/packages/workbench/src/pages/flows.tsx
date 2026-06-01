import { useAtom, useAtomRefresh, useAtomSet, useAtomValue } from "@effect/atom-react";
import {
  Workflow,
  Plus,
  Square,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  Loader2,
  Info,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  activeActionAtom,
  encodeJsonUnknownString,
  flowBlueprintAtom,
  flowBlueprintsAtom,
  flowExpandedAtom,
  flowsAtom,
  flowsStartDialogOpenAtom,
  parseJsonUnknown,
  resultData,
  resultError,
  resultLoading,
  startFlowAtom,
  startFlowFormAtom,
  stopFlowAtom,
} from "@/atoms/workbench";
import { Dialog } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";

function StartFlowDialog() {
  const [open, setOpen] = useAtom(flowsStartDialogOpenAtom);
  const [form, setForm] = useAtom(startFlowFormAtom);
  const startFlow = useAtomSet(startFlowAtom);
  const blueprintsResult = useAtomValue(flowBlueprintsAtom);
  const blueprints = resultData(blueprintsResult, []);
  const blueprintDetail = resultData(useAtomValue(flowBlueprintAtom(form.blueprint)), null) as Record<string, unknown> | null;
  const loadingBlueprints = resultLoading(blueprintsResult, blueprints);
  const isValid = form.id.trim().length > 0 && form.blueprint.length > 0 && form.description.trim().length > 0;

  const close = () => {
    setForm({
      id: "",
      blueprint: "",
      description: "",
      paramsJson: "{}",
      submitting: false,
      paramsError: null,
      submitted: false,
      definitionExpanded: false,
    });
    setOpen(false);
  };

  return (
    <Dialog
      open={open}
      onClose={close}
      title="Start Flow"
      footer={
        <>
          <button
            onClick={close}
            disabled={form.submitting}
            className="rounded-lg border border-border px-4 py-2 text-sm text-fg-muted hover:bg-surface-200 disabled:opacity-40"
          >
            Cancel
          </button>
          <button
            onClick={() => {
              setForm({ ...form, submitted: true });
              if (!isValid) return;
              const parameters = parseJsonUnknown(form.paramsJson);
              if (parameters === undefined || typeof parameters !== "object" || parameters === null || Array.isArray(parameters)) {
                setForm({ ...form, paramsError: "Invalid JSON", submitted: true });
                return;
              }
              startFlow({
                id: form.id.trim(),
                blueprint: form.blueprint,
                description: form.description.trim(),
                parameters: parameters as Record<string, unknown>,
              });
              close();
            }}
            disabled={form.submitting}
            className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-500 disabled:opacity-40"
          >
            {form.submitting && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            <Plus className="h-3.5 w-3.5" />
            Start
          </button>
        </>
      }
    >
      <div className="space-y-3">
        <label className="block">
          <span className="mb-1 block text-sm font-medium text-fg-muted">Flow ID</span>
          <input
            value={form.id}
            onChange={(event) => setForm({ ...form, id: event.target.value })}
            placeholder="my-flow-id"
            className="w-full rounded-lg border border-border bg-surface-100 px-3 py-2 text-sm text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
          {form.submitted && form.id.trim().length === 0 && (
            <p className="mt-1 text-xs text-red-400">Flow ID is required</p>
          )}
        </label>

        <label className="block">
          <span className="mb-1 block text-sm font-medium text-fg-muted">Blueprint</span>
          {loadingBlueprints ? (
            <div className="flex items-center gap-2 py-2 text-xs text-fg-subtle">
              <Loader2 className="h-3 w-3 animate-spin" /> Loading blueprints...
            </div>
          ) : (
            <select
              value={form.blueprint}
              onChange={(event) => setForm({ ...form, blueprint: event.target.value })}
              className="w-full rounded-lg border border-border bg-surface-100 px-3 py-2 text-sm text-fg focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            >
              <option value="">Select a blueprint</option>
              {blueprints.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          )}
          {form.submitted && form.blueprint.length === 0 && (
            <p className="mt-1 text-xs text-red-400">Blueprint is required</p>
          )}
        </label>

        {blueprintDetail !== null && (
          <div className="rounded-lg border border-border bg-surface-50 p-3">
            <button
              type="button"
              onClick={() => setForm({ ...form, definitionExpanded: !form.definitionExpanded })}
              className="flex w-full items-center gap-1.5 text-left text-xs font-medium text-fg-muted"
            >
              {form.definitionExpanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
              <Info className="h-3.5 w-3.5 text-brand-400" />
              Blueprint Details
            </button>
            {form.definitionExpanded && (
              <pre className="mt-2 max-h-48 overflow-auto rounded-md bg-surface-100 p-2 font-mono text-[10px] text-fg-muted">
                {encodeJsonUnknownString(blueprintDetail)}
              </pre>
            )}
          </div>
        )}

        <label className="block">
          <span className="mb-1 block text-sm font-medium text-fg-muted">Description</span>
          <input
            value={form.description}
            onChange={(event) => setForm({ ...form, description: event.target.value })}
            placeholder="What this flow does"
            className="w-full rounded-lg border border-border bg-surface-100 px-3 py-2 text-sm text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
          {form.submitted && form.description.trim().length === 0 && (
            <p className="mt-1 text-xs text-red-400">Description is required</p>
          )}
        </label>

        <label className="block">
          <span className="mb-1 block text-sm font-medium text-fg-muted">Parameters JSON</span>
          <textarea
            value={form.paramsJson}
            onChange={(event) => setForm({ ...form, paramsJson: event.target.value, paramsError: null })}
            rows={6}
            className="w-full resize-none rounded-lg border border-border bg-surface-100 px-3 py-2 font-mono text-xs text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
          {form.paramsError !== null && <p className="mt-1 text-xs text-red-400">{form.paramsError}</p>}
        </label>
      </div>
    </Dialog>
  );
}

export default function FlowsPage() {
  const flowsResult = useAtomValue(flowsAtom);
  const refreshFlows = useAtomRefresh(flowsAtom);
  const [expanded, setExpanded] = useAtom(flowExpandedAtom);
  const setStartOpen = useAtomSet(flowsStartDialogOpenAtom);
  const stopFlow = useAtomSet(stopFlowAtom);
  const actionInProgress = useAtomValue(activeActionAtom);
  const flows = resultData(flowsResult, []);
  const loading = resultLoading(flowsResult, flows);
  const error = resultError(flowsResult);

  return (
    <div className="flex h-full flex-col">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <Workflow className="h-6 w-6 text-brand-400" />
          <h1 className="text-2xl font-bold text-fg">Flows</h1>
          {!loading && <Badge>{flows.length} flow{flows.length !== 1 ? "s" : ""}</Badge>}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={refreshFlows}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-sm text-fg-muted transition-colors hover:bg-surface-200 disabled:opacity-40"
          >
            <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
            Refresh
          </button>
          <button
            onClick={() => setStartOpen(true)}
            className="flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-500"
          >
            <Plus className="h-3.5 w-3.5" />
            Start Flow
          </button>
        </div>
      </div>

      {loading && flows.length === 0 && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="mr-2 h-5 w-5 animate-spin text-fg-subtle" />
          <span className="text-fg-subtle">Loading flows...</span>
        </div>
      )}

      {error !== null && (
        <p className="mb-4 rounded-lg bg-error/10 px-4 py-2 text-sm text-error">
          {error}
        </p>
      )}

      {!loading && error === null && flows.length === 0 && (
        <div className="flex flex-1 flex-col items-center justify-center">
          <Workflow className="mb-3 h-10 w-10 text-fg-subtle opacity-30" />
          <p className="text-fg-subtle">No flows are running.</p>
        </div>
      )}

      {flows.length > 0 && (
        <div className="space-y-3">
          {flows.map((flow) => {
            const isExpanded = expanded[flow.id] === true;
            return (
              <div key={flow.id} className="rounded-lg border border-border bg-surface-50">
                <div className="flex items-center justify-between gap-3 px-4 py-3">
                  <button
                    onClick={() => setExpanded({ ...expanded, [flow.id]: !isExpanded })}
                    className="flex min-w-0 flex-1 items-center gap-2 text-left"
                  >
                    {isExpanded ? <ChevronDown className="h-4 w-4 text-fg-subtle" /> : <ChevronRight className="h-4 w-4 text-fg-subtle" />}
                    <span className="truncate font-mono text-sm font-medium text-fg">{flow.id}</span>
                    {flow.description !== undefined && (
                      <span className="truncate text-xs text-fg-muted">{flow.description}</span>
                    )}
                  </button>
                  <button
                    onClick={() => stopFlow(flow.id)}
                    disabled={actionInProgress === flow.id}
                    aria-label={`Stop flow ${flow.id}`}
                    className="flex items-center gap-1.5 rounded px-2.5 py-1.5 text-xs font-medium text-error hover:bg-error/10 disabled:opacity-40"
                  >
                    {actionInProgress === flow.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Square className="h-3.5 w-3.5" />}
                    Stop
                  </button>
                </div>
                {isExpanded && (
                  <div className="border-t border-border px-4 py-3">
                    <pre className="max-h-96 overflow-auto rounded-md bg-surface-100 p-3 font-mono text-xs text-fg-muted">
                      {encodeJsonUnknownString(flow)}
                    </pre>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      <StartFlowDialog />
    </div>
  );
}
