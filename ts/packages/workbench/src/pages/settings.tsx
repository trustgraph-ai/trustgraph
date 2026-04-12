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
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useSettings } from "@/providers/settings-provider";
import { useSocket } from "@/providers/socket-provider";
import { useConnectionState } from "@/providers/socket-provider";
import { useFlows } from "@/hooks/use-flows";
import { useSessionStore } from "@/hooks/use-session-store";
import { useNotification } from "@/providers/notification-provider";
import { Badge } from "@/components/ui/badge";

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

  // Dark mode toggle -- uses a class on <html>/<body> and persists to localStorage
  const [isDark, setIsDark] = useState(() => {
    if (typeof window === "undefined") return true;
    const saved = localStorage.getItem("tg-theme");
    if (saved) return saved === "dark";
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

  // Fetch collections
  useEffect(() => {
    let cancelled = false;
    setLoadingCollections(true);
    socket
      .collectionManagement()
      .listCollections()
      .then((cols) => {
        if (!cancelled) {
          setCollections(
            Array.isArray(cols)
              ? (cols as Array<{ id?: string; name?: string; [key: string]: unknown }>)
              : [],
          );
        }
      })
      .catch(() => {
        /* silent -- collections endpoint may not be available */
      })
      .finally(() => {
        if (!cancelled) setLoadingCollections(false);
      });
    return () => {
      cancelled = true;
    };
  }, [socket]);

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
              The WebSocket URL for the TrustGraph gateway.
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
              <select
                id="settings-collection"
                value={settings.collection}
                onChange={(e) => updateSetting("collection", e.target.value)}
                className="w-full rounded-lg border border-border bg-surface-100 px-4 py-2 text-sm text-fg focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              >
                {collections.map((c) => {
                  const id = c.id ?? String(c.name ?? c);
                  return (
                    <option key={id} value={id}>
                      {c.name ?? id}
                    </option>
                  );
                })}
              </select>
            ) : (
              <input
                id="settings-collection"
                type="text"
                value={settings.collection}
                onChange={(e) => updateSetting("collection", e.target.value)}
                className="w-full rounded-lg border border-border bg-surface-100 px-4 py-2 text-sm text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            )}
          </div>
        </Section>

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
                    {f.description ? ` -- ${f.description}` : ""}
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
          {Object.entries(settings.featureSwitches).map(([key, enabled]) => (
            <div key={key} className="flex items-center justify-between">
              <div>
                <p className="text-sm text-fg">{featureLabel(key)}</p>
              </div>
              <button
                role="switch"
                aria-checked={enabled}
                aria-label={featureLabel(key)}
                onClick={() => updateFeatureSwitches({ [key]: !enabled })}
                className={cn(
                  "relative inline-flex h-6 w-11 items-center rounded-full transition-colors",
                  enabled ? "bg-brand-600" : "bg-fg-subtle",
                )}
              >
                <span className={cn(
                  "inline-block h-4 w-4 rounded-full bg-white transition-transform",
                  enabled ? "translate-x-6" : "translate-x-1",
                )} />
              </button>
            </div>
          ))}
        </Section>

        {/* About */}
        <Section
          title="About"
          icon={<Info className="h-4 w-4 text-fg-subtle" />}
        >
          <div className="space-y-2 text-sm text-fg-muted">
            <p>
              <span className="font-medium text-fg">TrustGraph Workbench</span>{" "}
              v0.1.0
            </p>
            <p>
              A web-based interface for interacting with the TrustGraph
              knowledge-graph system.
            </p>
          </div>
        </Section>
      </div>
    </div>
  );
}
