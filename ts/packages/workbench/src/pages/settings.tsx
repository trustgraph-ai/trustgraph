import { useAtom, useAtomSet, useAtomValue } from "@effect/atom-react";
import {
  Settings as SettingsIcon,
  Wifi,
  WifiOff,
  Key,
  Eye,
  EyeOff,
  Database,
  Workflow,
  Info,
  Moon,
  Sun,
  Plus,
  Trash2,
} from "lucide-react";
import type * as React from "react";
import {
  collectionFormAtom,
  collectionsAtom,
  connectionStateAtom,
  createCollectionAtom,
  createCollectionDialogOpenAtom,
  deleteCollectionAtom,
  deleteCollectionDialogOpenAtom,
  flowIdAtom,
  flowsAtom,
  resultData,
  settingsAtom,
  settingsShowApiKeyAtom,
  setSettingsFieldAtom,
  themeAtom,
  toggleThemeAtom,
  updateFeatureSwitchesAtom,
} from "@/atoms/workbench";
import { Badge } from "@/components/ui/badge";
import { Dialog } from "@/components/ui/dialog";

const ACRONYMS: Record<string, string> = { mcp: "MCP", llm: "LLM", api: "API" };

function featureLabel(key: string): string {
  return key
    .replace(/([A-Z])/g, " $1")
    .trim()
    .split(" ")
    .map((word) => ACRONYMS[word.toLowerCase()] ?? word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function Section({
  title,
  icon,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-border bg-surface-50 p-5">
      <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold text-fg">
        {icon}
        {title}
      </h2>
      <div className="space-y-4">{children}</div>
    </div>
  );
}

export default function SettingsPage() {
  const settings = useAtomValue(settingsAtom);
  const setField = useAtomSet(setSettingsFieldAtom);
  const updateFeatureSwitches = useAtomSet(updateFeatureSwitchesAtom);
  const connectionState = useAtomValue(connectionStateAtom);
  const flows = resultData(useAtomValue(flowsAtom), []);
  const [flowId, setFlowId] = useAtom(flowIdAtom);
  const [showApiKey, setShowApiKey] = useAtom(settingsShowApiKeyAtom);
  const [theme] = useAtom(themeAtom);
  const toggleTheme = useAtomSet(toggleThemeAtom);
  const collections = resultData(useAtomValue(collectionsAtom), []);
  const [createOpen, setCreateOpen] = useAtom(createCollectionDialogOpenAtom);
  const [deleteOpen, setDeleteOpen] = useAtom(deleteCollectionDialogOpenAtom);
  const [collectionForm, setCollectionForm] = useAtom(collectionFormAtom);
  const createCollection = useAtomSet(createCollectionAtom);
  const deleteCollection = useAtomSet(deleteCollectionAtom);

  const isConnected =
    connectionState.status === "connected" ||
    connectionState.status === "authenticated" ||
    connectionState.status === "unauthenticated";
  const isWarning = connectionState.status === "unauthenticated";
  const statusBadge = isConnected ? (
    <Badge variant={isWarning ? "info" : "success"}>
      <Wifi className="h-3 w-3" /> {isWarning ? "Connected (no auth)" : connectionState.status}
    </Badge>
  ) : (
    <Badge variant="error">
      <WifiOff className="h-3 w-3" /> {connectionState.status}
    </Badge>
  );

  return (
    <div className="flex h-full flex-col">
      <div className="mb-6 flex items-center gap-3">
        <SettingsIcon className="h-6 w-6 text-brand-400" />
        <h1 className="text-2xl font-bold text-fg">Settings</h1>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Section title="Connection" icon={<Wifi className="h-4 w-4 text-brand-400" />}>
          <div className="flex items-center justify-between rounded-lg border border-border bg-surface-100 px-4 py-3">
            <div>
              <p className="text-sm font-medium text-fg">Gateway status</p>
              {connectionState.lastError !== undefined && (
                <p className="mt-0.5 text-xs text-error">{connectionState.lastError}</p>
              )}
            </div>
            {statusBadge}
          </div>

          <label className="block">
            <span className="mb-1 flex items-center gap-1.5 text-sm font-medium text-fg-muted">
              <Key className="h-3.5 w-3.5" /> API Key
            </span>
            <div className="relative">
              <input
                type={showApiKey ? "text" : "password"}
                value={settings.apiKey}
                onChange={(event) => setField({ key: "apiKey", value: event.target.value })}
                placeholder="Optional gateway bearer token"
                className="w-full rounded-lg border border-border bg-surface-100 px-3 py-2 pr-10 text-sm text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
              <button
                type="button"
                onClick={() => setShowApiKey(!showApiKey)}
                aria-label={showApiKey ? "Hide API key" : "Show API key"}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-fg-subtle hover:text-fg"
              >
                {showApiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </label>

          <label className="block">
            <span className="mb-1 block text-sm font-medium text-fg-muted">Gateway URL</span>
            <input
              type="text"
              value={settings.gatewayUrl}
              onChange={(event) => setField({ key: "gatewayUrl", value: event.target.value })}
              placeholder="/api/v1/rpc"
              className="w-full rounded-lg border border-border bg-surface-100 px-3 py-2 text-sm text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </label>

          <label className="block">
            <span className="mb-1 block text-sm font-medium text-fg-muted">User</span>
            <input
              type="text"
              value={settings.user}
              onChange={(event) => setField({ key: "user", value: event.target.value })}
              className="w-full rounded-lg border border-border bg-surface-100 px-3 py-2 text-sm text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </label>
        </Section>

        <Section title="Workspace" icon={<Database className="h-4 w-4 text-brand-400" />}>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-fg-muted">Collection</span>
            <div className="flex gap-2">
              <select
                value={settings.collection}
                onChange={(event) => setField({ key: "collection", value: event.target.value })}
                className="min-w-0 flex-1 rounded-lg border border-border bg-surface-100 px-3 py-2 text-sm text-fg focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              >
                {collections.map((collection) => {
                  const id = String(collection.collection ?? collection.id ?? collection.name ?? "default");
                  return (
                    <option key={id} value={id}>
                      {id}
                    </option>
                  );
                })}
              </select>
              <button
                type="button"
                onClick={() => setCreateOpen(true)}
                className="rounded-lg border border-border px-3 py-2 text-fg-muted hover:bg-surface-200 hover:text-fg"
                aria-label="Create collection"
              >
                <Plus className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={() => setDeleteOpen(true)}
                className="rounded-lg border border-border px-3 py-2 text-error hover:bg-error/10"
                aria-label="Delete collection"
                disabled={settings.collection === "default"}
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          </label>

          <label className="block">
            <span className="mb-1 flex items-center gap-1.5 text-sm font-medium text-fg-muted">
              <Workflow className="h-3.5 w-3.5" /> Flow
            </span>
            <select
              value={flowId}
              onChange={(event) => setFlowId(event.target.value)}
              className="w-full rounded-lg border border-border bg-surface-100 px-3 py-2 text-sm text-fg focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            >
              <option value="default">default</option>
              {flows.map((flow) => (
                <option key={flow.id} value={flow.id}>
                  {flow.id}
                </option>
              ))}
            </select>
          </label>

          <button
            type="button"
            onClick={() => toggleTheme(null)}
            className="flex w-full items-center justify-between rounded-lg border border-border bg-surface-100 px-4 py-3 text-sm text-fg hover:bg-surface-200"
          >
            <span className="flex items-center gap-2">
              {theme === "dark" ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
              Theme
            </span>
            <span className="capitalize text-fg-muted">{theme}</span>
          </button>
        </Section>

        <Section title="Feature Switches" icon={<Info className="h-4 w-4 text-brand-400" />}>
          <div className="grid gap-2 sm:grid-cols-2">
            {Object.entries(settings.featureSwitches).map(([key, value]) => (
              <label
                key={key}
                className="flex items-center justify-between rounded-lg border border-border bg-surface-100 px-3 py-2 text-sm"
              >
                <span className="text-fg-muted">{featureLabel(key)}</span>
                <input
                  type="checkbox"
                  checked={value}
                  onChange={(event) => updateFeatureSwitches({ [key]: event.target.checked })}
                  className="h-4 w-4 accent-brand-500"
                />
              </label>
            ))}
          </div>
        </Section>
      </div>

      <Dialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="Create Collection"
        footer={
          <>
            <button
              onClick={() => setCreateOpen(false)}
              className="rounded-lg border border-border px-4 py-2 text-sm text-fg-muted hover:bg-surface-200"
            >
              Cancel
            </button>
            <button
              onClick={() => {
                if (collectionForm.id.trim().length === 0) return;
                createCollection(collectionForm);
                setCollectionForm({ id: "", name: "", description: "", tags: "", submitting: false });
                setCreateOpen(false);
              }}
              disabled={collectionForm.id.trim().length === 0}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-500 disabled:opacity-40"
            >
              Create
            </button>
          </>
        }
      >
        <div className="space-y-3">
          {[
            ["id", "Collection ID", "research"] as const,
            ["name", "Display Name", "Research"] as const,
            ["description", "Description", "Optional description"] as const,
            ["tags", "Tags", "comma, separated"] as const,
          ].map(([key, label, placeholder]) => (
            <label key={key} className="block">
              <span className="mb-1 block text-sm font-medium text-fg-muted">{label}</span>
              <input
                value={collectionForm[key]}
                onChange={(event) => setCollectionForm({ ...collectionForm, [key]: event.target.value })}
                placeholder={placeholder}
                className="w-full rounded-lg border border-border bg-surface-100 px-3 py-2 text-sm text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            </label>
          ))}
        </div>
      </Dialog>

      <Dialog
        open={deleteOpen}
        onClose={() => setDeleteOpen(false)}
        title="Delete Collection"
        footer={
          <>
            <button
              onClick={() => setDeleteOpen(false)}
              className="rounded-lg border border-border px-4 py-2 text-sm text-fg-muted hover:bg-surface-200"
            >
              Cancel
            </button>
            <button
              onClick={() => {
                deleteCollection(settings.collection);
                setDeleteOpen(false);
              }}
              className="rounded-lg bg-error px-4 py-2 text-sm font-medium text-white hover:opacity-90"
            >
              Delete
            </button>
          </>
        }
      >
        <div className="flex items-start gap-3">
          <Trash2 className="mt-0.5 h-5 w-5 shrink-0 text-error" />
          <p className="text-sm text-fg-muted">
            Delete <span className="font-mono text-fg">{settings.collection}</span> and its data?
          </p>
        </div>
      </Dialog>
    </div>
  );
}
