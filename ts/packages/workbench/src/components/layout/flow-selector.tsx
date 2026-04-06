import { Workflow, Database } from "lucide-react";
import { useSessionStore } from "@/hooks/use-session-store";
import { useSettings } from "@/providers/settings-provider";

/**
 * Compact badge showing the active flow and collection.
 * Will be expanded later into a popover picker.
 */
export function FlowSelector() {
  const flowId = useSessionStore((s) => s.flowId);
  const collection = useSettings((s) => s.settings.collection);

  return (
    <div className="flex items-center gap-4 rounded-lg border border-border bg-surface-100 px-3 py-1.5 text-xs text-fg-muted">
      <span className="flex items-center gap-1.5">
        <Database className="h-3.5 w-3.5" />
        {collection}
      </span>
      <span className="flex items-center gap-1.5">
        <Workflow className="h-3.5 w-3.5" />
        {flowId || "<none>"}
      </span>
    </div>
  );
}
