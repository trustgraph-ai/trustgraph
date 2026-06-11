import { useAtom, useAtomRefresh, useAtomValue } from "@effect/atom-react";
import {
  MessageCircleCode,
  Loader2,
  RefreshCw,
  ChevronRight,
  X,
  FileText,
  Terminal,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  promptActiveTabAtom,
  promptDetailAtom,
  promptsAtom,
  resultData,
  resultError,
  resultLoading,
  selectedPromptIdAtom,
  systemPromptAtom,
} from "@/atoms/workbench";

export default function PromptsPage() {
  const promptsResult = useAtomValue(promptsAtom);
  const systemPromptResult = useAtomValue(systemPromptAtom);
  const refreshPrompts = useAtomRefresh(promptsAtom);
  const refreshSystemPrompt = useAtomRefresh(systemPromptAtom);
  const [activeTab, setActiveTab] = useAtom(promptActiveTabAtom);
  const [selectedPromptId, setSelectedPromptId] = useAtom(selectedPromptIdAtom);
  const promptDetailResult = useAtomValue(promptDetailAtom(selectedPromptId ?? ""));

  const prompts = resultData(promptsResult, []);
  const systemPrompt = resultData(systemPromptResult, "");
  const loading = resultLoading(promptsResult, prompts) || resultLoading(systemPromptResult, systemPrompt);
  const error = resultError(promptsResult) ?? resultError(systemPromptResult);
  const promptDetail = resultData(promptDetailResult, null) as { system?: string; prompt?: string } | string | null;
  const loadingDetail = selectedPromptId !== null && resultLoading(promptDetailResult, promptDetail);

  const refresh = () => {
    refreshPrompts();
    refreshSystemPrompt();
  };

  return (
    <div className="flex h-full flex-col">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <MessageCircleCode className="h-6 w-6 text-brand-400" />
          <h1 className="text-2xl font-bold text-fg">Prompts</h1>
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

      <div role="tablist" aria-label="Prompt sections" className="mb-4 flex gap-1 rounded-lg bg-surface-100 p-1">
        <button
          id="tab-templates"
          role="tab"
          aria-selected={activeTab === "templates"}
          onClick={() => setActiveTab("templates")}
          className={cn(
            "flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors",
            activeTab === "templates" ? "bg-surface-50 text-fg shadow-sm" : "text-fg-muted hover:text-fg",
          )}
        >
          <FileText className="h-3.5 w-3.5" />
          Templates
        </button>
        <button
          id="tab-system"
          role="tab"
          aria-selected={activeTab === "system"}
          onClick={() => setActiveTab("system")}
          className={cn(
            "flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors",
            activeTab === "system" ? "bg-surface-50 text-fg shadow-sm" : "text-fg-muted hover:text-fg",
          )}
        >
          <Terminal className="h-3.5 w-3.5" />
          System Prompt
        </button>
      </div>

      {error !== null && (
        <p className="mb-4 rounded-lg bg-error/10 px-4 py-2 text-sm text-error">
          {error}
        </p>
      )}

      {activeTab === "templates" && (
        <div id="panel-templates" role="tabpanel" aria-labelledby="tab-templates" className="flex flex-1 flex-col gap-4 overflow-hidden">
          {loading && prompts.length === 0 && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="mr-2 h-5 w-5 animate-spin text-fg-subtle" />
              <span className="text-fg-subtle">Loading prompts...</span>
            </div>
          )}

          {!loading && prompts.length === 0 && (
            <div className="flex flex-1 flex-col items-center justify-center">
              <FileText className="mb-3 h-10 w-10 text-fg-subtle opacity-30" />
              <p className="text-fg-subtle">No prompt templates found.</p>
            </div>
          )}

          {prompts.length > 0 && (
            <div className="flex flex-1 flex-col gap-4 overflow-hidden lg:flex-row">
              <div className="max-h-56 w-full shrink-0 overflow-y-auto rounded-lg border border-border lg:max-h-none lg:w-80">
                <div className="border-b border-border bg-surface-100 px-4 py-3">
                  <h2 className="text-xs font-medium uppercase tracking-wider text-fg-muted">
                    Templates ({prompts.length})
                  </h2>
                </div>
                <div className="divide-y divide-border">
                  {prompts.map((prompt) => {
                    const id = prompt.id ?? (prompt as Record<string, unknown>).name ?? String(prompt);
                    return (
                      <button
                        key={String(id)}
                        onClick={() => setSelectedPromptId(String(id))}
                        className={cn(
                          "flex w-full items-center justify-between px-4 py-3 text-left text-sm transition-colors",
                          selectedPromptId === String(id)
                            ? "bg-brand-600/10 text-brand-400"
                            : "text-fg hover:bg-surface-100",
                        )}
                      >
                        <span className="truncate font-mono text-xs">{String(id)}</span>
                        <ChevronRight className="h-3.5 w-3.5 shrink-0 text-fg-subtle" />
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="min-h-0 flex flex-1 flex-col overflow-hidden rounded-lg border border-border">
                {selectedPromptId !== null && selectedPromptId.length > 0 ? (
                  <>
                    <div className="flex items-center justify-between border-b border-border bg-surface-100 px-4 py-3">
                      <h2 className="text-sm font-medium text-fg">
                        <span className="font-mono">{selectedPromptId}</span>
                      </h2>
                      <button
                        onClick={() => setSelectedPromptId(null)}
                        aria-label="Close prompt detail"
                        className="rounded-md p-1 text-fg-subtle hover:bg-surface-200 hover:text-fg"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                    <div className="flex-1 overflow-y-auto p-4">
                      {loadingDetail ? (
                        <div className="flex items-center gap-2 py-4 text-fg-subtle">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          Loading...
                        </div>
                      ) : promptDetail !== null && typeof promptDetail === "object" ? (
                        <div className="space-y-4">
                          {promptDetail.system !== undefined && promptDetail.system.length > 0 && (
                            <section>
                              <h3 className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-fg-subtle">
                                System
                              </h3>
                              <pre className="whitespace-pre-wrap rounded-md border border-border bg-surface-100 p-3 font-mono text-xs text-fg-muted">
                                {promptDetail.system}
                              </pre>
                            </section>
                          )}
                          {promptDetail.prompt !== undefined && promptDetail.prompt.length > 0 && (
                            <section>
                              <h3 className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-fg-subtle">
                                Prompt
                              </h3>
                              <pre className="whitespace-pre-wrap rounded-md border border-border bg-surface-100 p-3 font-mono text-xs text-fg-muted">
                                {promptDetail.prompt}
                              </pre>
                            </section>
                          )}
                        </div>
                      ) : (
                        <pre className="whitespace-pre-wrap font-mono text-xs text-fg-muted">
                          {typeof promptDetail === "string" ? promptDetail : ""}
                        </pre>
                      )}
                    </div>
                  </>
                ) : (
                  <div className="flex flex-1 items-center justify-center text-fg-subtle">
                    Select a template to view its contents.
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === "system" && (
        <div id="panel-system" role="tabpanel" aria-labelledby="tab-system" className="flex flex-1 flex-col overflow-hidden rounded-lg border border-border">
          <div className="border-b border-border bg-surface-100 px-4 py-3">
            <h2 className="text-xs font-medium uppercase tracking-wider text-fg-muted">
              System Prompt
            </h2>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            {loading ? (
              <div className="flex items-center gap-2 py-4 text-fg-subtle">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading...
              </div>
            ) : systemPrompt.length > 0 ? (
              <pre className="whitespace-pre-wrap font-mono text-xs text-fg-muted">
                {systemPrompt}
              </pre>
            ) : (
              <p className="text-sm text-fg-subtle">No system prompt configured.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
