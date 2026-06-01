import { useAtomValue } from "@effect/atom-react";
import { Workflow, Database } from "lucide-react";
import { flowIdAtom, settingsAtom } from "@/atoms/workbench";

/**
 * Compact badge showing the active flow and collection.
 * Will be expanded later into a popover picker.
 */
export function FlowSelector() {
  const flowId = useAtomValue(flowIdAtom);
  const collection = useAtomValue(settingsAtom).collection;

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
