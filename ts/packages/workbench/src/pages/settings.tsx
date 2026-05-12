import { useCallback, useEffect, useState } from "react";
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
  Loader2,
  Moon,
  Sun,
  Plus,
  Trash2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useSettings } from "@/providers/settings-provider";
import { useSocket } from "@/providers/socket-provider";
import { useConnectionState } from "@/providers/socket-provider";
import { useFlows } from "@/hooks/use-flows";
import { useSessionStore } from "@/hooks/use-session-store";
import { useNotification } from "@/providers/notification-provider";
import { Badge } from "@/components/ui/badge";
import { Dialog } from "@/components/ui/dialog";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const ACRONYMS: Record<string, string> = { mcp: "MCP", llm: "LLM", api: "API" };

/** Convert camelCase key to display label, preserving known acronyms. */
function featureLabel(key: string): string {
  return key
    .replace(/([A-Z])/g, " $1")
    .trim()
    .split(" ")
    .map((w) => ACRONYMS[w.toLowerCase()] ?? w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

// ---------------------------------------------------------------------------
// Section wrapper
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Settings page
// ---------------------------------------------------------------------------

export default function SettingsPage() {
  const { settings, updateSetting, updateFeatureSwitches } = useSettings();
  const connectionState = useConnectionState();
  const socket = useSocket();
  const { flows } = useFlows();
  const notify = useNotification();

  const flowId = useSessionStore((s) => s.flowId);
  const setFlowId = useSessionStore((s) => s.setFlowId);

  const [showApiKey, setShowApiKey] = useState(false);
  const [collections, setCollections] = useState<
    Array<{ id?: string; name?: string; [key: string]: unknown }>
  >([]);
  const [loadingCollections, setLoadingCollections] = useState(false);

  // Create-collection dialog state
  const [createOpen, setCreateOpen] = useState(false);
  const [newId, setNewId] = useState("");
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newTags, setNewTags] = useState("");
  const [creating, setCreating] = useState(false);

  // Delete-collection confirmation dialog state
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // Dark mode toggle -- uses a class on <html>/<body> and persists to localStorage
  const [isDark, setIsDark] = useState(() => {
    if (typeof window === "undefined") return true;
    const saved = localStorage.getItem("tg-theme");
    if (saved !== null) return saved === "dark";
    return !document.documentElement.classList.contains("light");
  });

  const toggleTheme = useCallback(() => {
    const next = !isDark;
    setIsDark(next);
    if (next) {
      document.documentElement.classList.remove("light");
      document.body.classList.remove("light");
      document.body.classList.add("dark");
      localStorage.setItem("tg-theme", "dark");
    } else {
      document.documentElement.classList.add("light");
      document.body.classList.add("light");
      document.body.classList.remove("dark");
      localStorage.setItem("tg-theme", "light");
    }
  }, [isDark]);

  // Reusable function to fetch collections from the backend
  const refreshCollections = useCallback(() => {
    setLoadingCollections(true);
    return socket
      .collectionManagement()
      .listCollections()
      .then((cols) => {
        const list = Array.isArray(cols)
          ? (cols as Array<{ id?: string; collection?: string; name?: string; [key: string]: unknown }>)
          : [];
        // Ensure "default" collection is always present
        const hasDefault = list.some(
          (c) => (c.collection ?? c.id ?? c.name) === "default",
        );
        if (!hasDefault) {
          list.unshift({ id: "default", collection: "default", name: "default" });
        }
        setCollections(list);
        return list;
      })
      .catch(() => {
        // Fallback: at minimum show "default"
        setCollections([{ id: "default", collection: "default", name: "default" }]);
      })
      .finally(() => {
        setLoadingCollections(false);
      });
  }, [socket]);

  // Fetch collections on mount
  useEffect(() => {
    let cancelled = false;
    refreshCollections().then(() => {
      if (cancelled) return;
    });
    return () => {
      cancelled = true;
    };
  }, [refreshCollections]);

  // Create a new collection
  const handleCreateCollection = useCallback(async () => {
    const trimmedId = newId.trim();
    if (trimmedId.length === 0) return;

    setCreating(true);
    try {
      const tags = newTags
        .split(",")
        .map((t) => t.trim())
        .filter((tag) => tag.length > 0);

      await socket
        .collectionManagement()
        .updateCollection(
          trimmedId,
          newName.trim().length > 0 ? newName.trim() : undefined,
          newDescription.trim().length > 0 ? newDescription.trim() : undefined,
          tags.length > 0 ? tags : undefined,
        );

      await refreshCollections();
      updateSetting("collection", trimmedId);
      notify.success("Collection created", `"${newName.trim() || trimmedId}" is now active.`);

      // Reset form and close
      setNewId("");
      setNewName("");
      setNewDescription("");
      setNewTags("");
      setCreateOpen(false);
    } catch (err) {
      notify.error(
        "Failed to create collection",
        err instanceof Error ? err.message : String(err),
      );
    } finally {
      setCreating(false);
    }
  }, [newId, newName, newDescription, newTags, socket, refreshCollections, updateSetting, notify]);

  // Delete the current collection
  const handleDeleteCollection = useCallback(async () => {
    const currentId = settings.collection;
    if (currentId.length === 0) return;

    setDeleting(true);
    try {
      await socket.collectionManagement().deleteCollection(currentId);
      await refreshCollections();

      // Switch to the first remaining collection
      const remaining = collections.filter((c) => {
        const id = c.id ?? String(c.name ?? c);
        return id !== currentId;
      });
      if (remaining.length > 0) {
        const firstId = remaining[0].id ?? String(remaining[0].name ?? remaining[0]);
        updateSetting("collection", firstId);
      }

      notify.success("Collection deleted", `"${currentId}" has been removed.`);
      setDeleteOpen(false);
    } catch (err) {
      notify.error(
        "Failed to delete collection",
        err instanceof Error ? err.message : String(err),
      );
    } finally {
      setDeleting(false);
    }
  }, [settings.collection, socket, refreshCollections, collections, updateSetting, notify]);

  // Connection status helpers
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
      {/* Header */}
      <div className="mb-6 flex items-center gap-3">
        <SettingsIcon className="h-6 w-6 text-brand-400" />
        <h1 className="text-2xl font-bold text-fg">Settings</h1>
      </div>

      {/* Form */}
      <div className="max-w-2xl space-y-5 pb-8 overflow-y-auto">
        {/* Connection */}
        <Section
          title="Connection"
          icon={<Wifi className="h-4 w-4 text-fg-subtle" />}
        >
          <div className="flex items-center gap-3">
            <span className="text-sm text-fg-muted">Status:</span>
            {statusBadge}
          </div>

          <div className="space-y-1.5">
            <label htmlFor="settings-gateway-url" className="block text-sm font-medium text-fg-muted">
              Gateway URL
            </label>
            <input
              id="settings-gateway-url"
              type="text"
              value={settings.gatewayUrl}
              onChange={(e) => updateSetting("gatewayUrl", e.target.value)}
              placeholder="Leave blank to use the default proxy"
              className="w-full rounded-lg border border-border bg-surface-100 px-4 py-2 text-sm text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
            <p className="text-xs text-fg-subtle">
              The WebSocket URL for the Beep Graph gateway.
            </p>
          </div>

          <div className="space-y-1.5">
            <label htmlFor="settings-user-id" className="block text-sm font-medium text-fg-muted">
              User ID
            </label>
            <input
              id="settings-user-id"
              type="text"
              value={settings.user}
              onChange={(e) => updateSetting("user", e.target.value)}
              className="w-full rounded-lg border border-border bg-surface-100 px-4 py-2 text-sm text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>
        </Section>

        {/* Authentication */}
        <Section
          title="Authentication"
          icon={<Key className="h-4 w-4 text-fg-subtle" />}
        >
          <div className="space-y-1.5">
            <label htmlFor="settings-api-key" className="block text-sm font-medium text-fg-muted">
              API Key
            </label>
            <div className="relative">
              <input
                id="settings-api-key"
                type={showApiKey ? "text" : "password"}
                value={settings.apiKey}
                onChange={(e) => updateSetting("apiKey", e.target.value)}
                placeholder="Leave blank for unauthenticated access"
                className="w-full rounded-lg border border-border bg-surface-100 px-4 py-2 pr-10 text-sm text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
              <button
                type="button"
                onClick={() => setShowApiKey((p) => !p)}
                aria-label={showApiKey ? "Hide API key" : "Show API key"}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-fg-subtle hover:text-fg"
              >
                {showApiKey ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
            <p className="text-xs text-fg-subtle">
              Changing the API key will reconnect the WebSocket.
            </p>
          </div>
        </Section>

        {/* Collection */}
        <Section
          title="Collection"
          icon={<Database className="h-4 w-4 text-fg-subtle" />}
        >
          <div className="space-y-1.5">
            <label htmlFor="settings-collection" className="block text-sm font-medium text-fg-muted">
              Active Collection
            </label>
            {loadingCollections ? (
              <div className="flex items-center gap-2 py-2 text-xs text-fg-subtle">
                <Loader2 className="h-3 w-3 animate-spin" /> Loading
                collections...
              </div>
            ) : collections.length > 0 ? (
              <div className="flex items-center gap-2">
                <select
                  id="settings-collection"
                  value={settings.collection}
                  onChange={(e) => updateSetting("collection", e.target.value)}
                  className="flex-1 rounded-lg border border-border bg-surface-100 px-4 py-2 text-sm text-fg focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                >
                  {collections.map((c) => {
                    const cObj = c as { collection?: string; id?: string; name?: string };
                    const collId = cObj.collection ?? cObj.id ?? String(cObj.name ?? c);
                    const label = cObj.name ?? collId;
                    return (
                      <option key={collId} value={collId}>
                        {label !== collId ? `${label} (${collId})` : collId}
                      </option>
                    );
                  })}
                </select>
                <button
                  type="button"
                  onClick={() => setCreateOpen(true)}
                  aria-label="New collection"
                  title="New collection"
                  className="rounded-lg border border-border bg-surface-100 p-2 text-fg-subtle hover:bg-surface-200 hover:text-fg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
                >
                  <Plus className="h-4 w-4" />
                </button>
                {collections.length > 1 && (
                  <button
                    type="button"
                    onClick={() => setDeleteOpen(true)}
                    aria-label="Delete collection"
                    title="Delete collection"
                    className="rounded-lg border border-red-500/30 bg-surface-100 p-2 text-red-400 hover:bg-red-500/10 hover:text-red-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <input
                  id="settings-collection"
                  type="text"
                  value={settings.collection}
                  onChange={(e) => updateSetting("collection", e.target.value)}
                  className="flex-1 rounded-lg border border-border bg-surface-100 px-4 py-2 text-sm text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
                <button
                  type="button"
                  onClick={() => setCreateOpen(true)}
                  aria-label="New collection"
                  title="New collection"
                  className="rounded-lg border border-border bg-surface-100 p-2 text-fg-subtle hover:bg-surface-200 hover:text-fg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
                >
                  <Plus className="h-4 w-4" />
                </button>
              </div>
            )}
          </div>
        </Section>

        {/* Create Collection Dialog */}
        <Dialog
          open={createOpen}
          onClose={() => setCreateOpen(false)}
          title="New Collection"
          footer={
            <>
              <button
                type="button"
                onClick={() => setCreateOpen(false)}
                className="rounded-lg border border-border px-4 py-2 text-sm text-fg-muted hover:bg-surface-200"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={newId.trim().length === 0 || creating}
                onClick={handleCreateCollection}
                className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {creating && <Loader2 className="h-3 w-3 animate-spin" />}
                Create
              </button>
            </>
          }
        >
          <div className="space-y-4">
            <div className="space-y-1.5">
              <label htmlFor="new-collection-id" className="block text-sm font-medium text-fg-muted">
                Collection ID <span className="text-red-400">*</span>
              </label>
              <input
                id="new-collection-id"
                type="text"
                value={newId}
                onChange={(e) => setNewId(e.target.value)}
                placeholder="my-collection"
                className="w-full rounded-lg border border-border bg-surface-100 px-4 py-2 text-sm text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
              <p className="text-xs text-fg-subtle">
                A unique identifier for this collection.
              </p>
            </div>

            <div className="space-y-1.5">
              <label htmlFor="new-collection-name" className="block text-sm font-medium text-fg-muted">
                Display Name
              </label>
              <input
                id="new-collection-name"
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="My Collection"
                className="w-full rounded-lg border border-border bg-surface-100 px-4 py-2 text-sm text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            </div>

            <div className="space-y-1.5">
              <label htmlFor="new-collection-description" className="block text-sm font-medium text-fg-muted">
                Description
              </label>
              <textarea
                id="new-collection-description"
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                placeholder="What this collection is for..."
                rows={3}
                className="w-full rounded-lg border border-border bg-surface-100 px-4 py-2 text-sm text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 resize-none"
              />
            </div>

            <div className="space-y-1.5">
              <label htmlFor="new-collection-tags" className="block text-sm font-medium text-fg-muted">
                Tags
              </label>
              <input
                id="new-collection-tags"
                type="text"
                value={newTags}
                onChange={(e) => setNewTags(e.target.value)}
                placeholder="research, finance, internal"
                className="w-full rounded-lg border border-border bg-surface-100 px-4 py-2 text-sm text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
              <p className="text-xs text-fg-subtle">
                Comma-separated list of tags for categorization.
              </p>
            </div>
          </div>
        </Dialog>

        {/* Delete Collection Confirmation Dialog */}
        <Dialog
          open={deleteOpen}
          onClose={() => setDeleteOpen(false)}
          title="Delete Collection"
          className="max-w-md"
          footer={
            <>
              <button
                type="button"
                onClick={() => setDeleteOpen(false)}
                className="rounded-lg border border-border px-4 py-2 text-sm text-fg-muted hover:bg-surface-200"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={deleting}
                onClick={handleDeleteCollection}
                className="inline-flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {deleting && <Loader2 className="h-3 w-3 animate-spin" />}
                Delete
              </button>
            </>
          }
        >
          <p className="text-sm text-fg-muted">
            Are you sure you want to delete the collection{" "}
            <span className="font-semibold text-fg">"{settings.collection}"</span>?
            This will remove the collection and all its data. This action cannot be undone.
          </p>
        </Dialog>

        {/* Flow */}
        <Section
          title="Active Flow"
          icon={<Workflow className="h-4 w-4 text-fg-subtle" />}
        >
          <div className="space-y-1.5">
            <label htmlFor="settings-flow" className="block text-sm font-medium text-fg-muted">
              Flow
            </label>
            {flows.length > 0 ? (
              <select
                id="settings-flow"
                value={flowId}
                onChange={(e) => setFlowId(e.target.value)}
                className="w-full rounded-lg border border-border bg-surface-100 px-4 py-2 text-sm text-fg focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              >
                <option value="default">default</option>
                {flows.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.id}
                    {f.description !== undefined && f.description.length > 0 ? ` -- ${f.description}` : ""}
                  </option>
                ))}
              </select>
            ) : (
              <input
                id="settings-flow"
                type="text"
                value={flowId}
                onChange={(e) => setFlowId(e.target.value)}
                placeholder="default"
                className="w-full rounded-lg border border-border bg-surface-100 px-4 py-2 text-sm text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            )}
            <p className="text-xs text-fg-subtle">
              The flow ID used for chat, graph queries, and document processing.
            </p>
          </div>
        </Section>

        {/* Theme */}
        <Section
          title="Appearance"
          icon={isDark ? <Moon className="h-4 w-4 text-fg-subtle" /> : <Sun className="h-4 w-4 text-fg-subtle" />}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-fg">Theme</p>
              <p className="text-xs text-fg-subtle">
                Toggle between dark and light mode.
              </p>
              <p className="text-xs text-fg-subtle">
                Currently using {isDark ? "dark" : "light"} mode.
              </p>
            </div>
            <button
              role="switch"
              aria-checked={isDark}
              aria-label="Dark mode"
              onClick={toggleTheme}
              className={cn(
                "relative inline-flex h-6 w-11 items-center rounded-full transition-colors",
                isDark ? "bg-brand-600" : "bg-fg-subtle",
              )}
            >
              <span
                className={cn(
                  "inline-block h-4 w-4 rounded-full bg-white transition-transform",
                  isDark ? "translate-x-6" : "translate-x-1",
                )}
              />
            </button>
          </div>
        </Section>

        {/* Feature Switches */}
        <Section
          title="Feature Switches"
          icon={<SettingsIcon className="h-4 w-4 text-fg-subtle" />}
        >
          {Object.entries(settings.featureSwitches).map(([key, enabled]) => {
            const isEnabled = enabled === true;
            return (
              <div key={key} className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-fg">{featureLabel(key)}</p>
                </div>
                <button
                  role="switch"
                  aria-checked={isEnabled}
                  aria-label={featureLabel(key)}
                  onClick={() => updateFeatureSwitches({ [key]: !isEnabled })}
                  className={cn(
                    "relative inline-flex h-6 w-11 items-center rounded-full transition-colors",
                    isEnabled ? "bg-brand-600" : "bg-fg-subtle",
                  )}
                >
                  <span className={cn(
                    "inline-block h-4 w-4 rounded-full bg-white transition-transform",
                    isEnabled ? "translate-x-6" : "translate-x-1",
                  )} />
                </button>
              </div>
            );
          })}
        </Section>

        {/* About */}
        <Section
          title="About"
          icon={<Info className="h-4 w-4 text-fg-subtle" />}
        >
          <div className="space-y-2 text-sm text-fg-muted">
            <p>
              <span className="font-medium text-fg">Beep Graph</span>{" "}
              v0.1.0
            </p>
            <p>
              A web-based interface for interacting with the Beep Graph
              knowledge-graph system.
            </p>
          </div>
        </Section>
      </div>
    </div>
  );
}
