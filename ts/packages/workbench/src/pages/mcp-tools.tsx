import { useCallback, useEffect, useState } from "react";
import {
  Plug,
  Server,
  Wrench,
  Plus,
  Pencil,
  Trash2,
  Eye,
  EyeOff,
  AlertTriangle,
  Loader2,
  RefreshCw,
  Lock,
  Tag,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Dialog } from "@/components/ui/dialog";
import { useNotification } from "@/providers/notification-provider";
import { useSettings } from "@/providers/settings-provider";
import {
  useMcpConfig,
  type McpServerConfig,
  type McpServerEntry,
  type ToolConfig,
  type ToolEntry,
  type ToolArgument,
} from "@/hooks/use-mcp-config";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

type Tab = "servers" | "tools";

const INPUT_CLASS =
  "w-full rounded-lg border border-border bg-surface-100 px-4 py-2 text-sm text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500";

const ARG_TYPES = ["string", "number", "boolean", "object"] as const;

// ---------------------------------------------------------------------------
// McpServerDialog
// ---------------------------------------------------------------------------

function McpServerDialog({
  open,
  onClose,
  onSave,
  initial,
  existingKeys,
}: {
  open: boolean;
  onClose: () => void;
  onSave: (key: string, config: McpServerConfig) => Promise<void>;
  initial?: McpServerEntry;
  existingKeys: string[];
}) {
  const isEditing = initial !== undefined;
  const [key, setKey] = useState(initial?.key ?? "");
  const [url, setUrl] = useState(initial?.config.url ?? "");
  const [remoteName, setRemoteName] = useState(
    initial?.config["remote-name"] ?? "",
  );
  const [authToken, setAuthToken] = useState(
    initial?.config["auth-token"] ?? "",
  );
  const [showToken, setShowToken] = useState(false);
  const [saving, setSaving] = useState(false);
  const [keyError, setKeyError] = useState("");

  // Reset form state when dialog opens
  useEffect(() => {
    if (open) {
      setKey(initial?.key ?? "");
      setUrl(initial?.config.url ?? "");
      setRemoteName(initial?.config["remote-name"] ?? "");
      setAuthToken(initial?.config["auth-token"] ?? "");
      setShowToken(false);
      setKeyError("");
    }
  }, [open, initial]);

  const handleSave = async () => {
    if (key.trim().length === 0 || url.trim().length === 0) return;
    if (!isEditing && existingKeys.includes(key.trim())) {
      setKeyError("A server with this key already exists");
      return;
    }
    const config: McpServerConfig = { url: url.trim() };
    if (remoteName.trim().length > 0) config["remote-name"] = remoteName.trim();
    if (authToken.trim().length > 0) config["auth-token"] = authToken.trim();
    setSaving(true);
    try {
      await onSave(key.trim(), config);
      onClose();
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={isEditing ? "Edit MCP Server" : "Add MCP Server"}
      footer={
        <>
          <button
            onClick={onClose}
            className="rounded-lg border border-border px-4 py-2 text-sm text-fg-muted hover:bg-surface-200"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={key.trim().length === 0 || url.trim().length === 0 || saving}
            className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-500 disabled:opacity-40"
          >
            {saving && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            Save
          </button>
        </>
      }
    >
      <div className="space-y-4">
        <div>
          <label htmlFor="server-key" className="mb-1 block text-sm font-medium text-fg">
            Key
          </label>
          <input
            id="server-key"
            type="text"
            value={key}
            onChange={(e) => {
              setKey(e.target.value);
              setKeyError("");
            }}
            disabled={isEditing}
            placeholder="brave-search"
            className={cn(INPUT_CLASS, isEditing && "opacity-60")}
          />
          {keyError.length > 0 && (
            <p className="mt-1 text-xs text-error">{keyError}</p>
          )}
        </div>
        <div>
          <label htmlFor="server-url" className="mb-1 block text-sm font-medium text-fg">
            URL
          </label>
          <input
            id="server-url"
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="http://localhost:8383/mcp"
            className={INPUT_CLASS}
          />
        </div>
        <div>
          <label htmlFor="server-remote-name" className="mb-1 block text-sm font-medium text-fg">
            Remote Name <span className="text-fg-subtle">(optional)</span>
          </label>
          <input
            id="server-remote-name"
            type="text"
            value={remoteName}
            onChange={(e) => setRemoteName(e.target.value)}
            placeholder="Tool name at the remote server"
            className={INPUT_CLASS}
          />
        </div>
        <div>
          <label htmlFor="server-auth-token" className="mb-1 block text-sm font-medium text-fg">
            Auth Token <span className="text-fg-subtle">(optional)</span>
          </label>
          <div className="relative">
            <input
              id="server-auth-token"
              type={showToken ? "text" : "password"}
              value={authToken}
              onChange={(e) => setAuthToken(e.target.value)}
              placeholder="Bearer token for authentication"
              className={cn(INPUT_CLASS, "pr-10")}
            />
            <button
              type="button"
              onClick={() => setShowToken(!showToken)}
              aria-label={showToken ? "Hide auth token" : "Show auth token"}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-fg-subtle hover:text-fg"
            >
              {showToken ? (
                <EyeOff className="h-4 w-4" />
              ) : (
                <Eye className="h-4 w-4" />
              )}
            </button>
          </div>
        </div>
      </div>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// McpToolDialog
// ---------------------------------------------------------------------------

function McpToolDialog({
  open,
  onClose,
  onSave,
  initial,
  existingKeys,
  serverKeys,
}: {
  open: boolean;
  onClose: () => void;
  onSave: (key: string, config: ToolConfig) => Promise<void>;
  initial?: ToolEntry;
  existingKeys: string[];
  serverKeys: string[];
}) {
  const isEditing = initial !== undefined;
  const [key, setKey] = useState(initial?.key ?? "");
  const [name, setName] = useState(initial?.config.name ?? "");
  const [description, setDescription] = useState(
    initial?.config.description ?? "",
  );
  const [mcpTool, setMcpTool] = useState(initial?.config["mcp-tool"] ?? "");
  const [group, setGroup] = useState(
    initial?.config.group?.join(", ") ?? "default",
  );
  const [args, setArgs] = useState<ToolArgument[]>(
    initial?.config.arguments ?? [],
  );
  const [saving, setSaving] = useState(false);
  const [keyError, setKeyError] = useState("");

  // Reset form state when dialog opens
  useEffect(() => {
    if (open) {
      setKey(initial?.key ?? "");
      setName(initial?.config.name ?? "");
      setDescription(initial?.config.description ?? "");
      setMcpTool(initial?.config["mcp-tool"] ?? "");
      setGroup(initial?.config.group?.join(", ") ?? "default");
      setArgs(initial?.config.arguments ?? []);
      setKeyError("");
    }
  }, [open, initial]);

  const addArg = () =>
    setArgs((prev) => [...prev, { name: "", type: "string", description: "" }]);

  const updateArg = (i: number, field: keyof ToolArgument, value: string) =>
    setArgs((prev) => prev.map((a, j) => (j === i ? { ...a, [field]: value } : a)));

  const removeArg = (i: number) =>
    setArgs((prev) => prev.filter((_, j) => j !== i));

  const handleSave = async () => {
    if (
      key.trim().length === 0 ||
      name.trim().length === 0 ||
      mcpTool.trim().length === 0
    ) return;
    if (!isEditing && existingKeys.includes(key.trim())) {
      setKeyError("A tool with this key already exists");
      return;
    }
    const config: ToolConfig = {
      type: "mcp-tool",
      name: name.trim(),
      description: description.trim(),
      "mcp-tool": mcpTool.trim(),
      group: group
        .split(",")
        .map((g) => g.trim())
        .filter((g) => g.length > 0),
      arguments: args.filter((a) => a.name.trim().length > 0),
    };
    setSaving(true);
    try {
      await onSave(key.trim(), config);
      onClose();
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={isEditing ? "Edit MCP Tool" : "Add MCP Tool"}
      className="max-w-2xl"
      footer={
        <>
          <button
            onClick={onClose}
            className="rounded-lg border border-border px-4 py-2 text-sm text-fg-muted hover:bg-surface-200"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={
              key.trim().length === 0 ||
              name.trim().length === 0 ||
              mcpTool.trim().length === 0 ||
              saving
            }
            className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-500 disabled:opacity-40"
          >
            {saving && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            Save
          </button>
        </>
      }
    >
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="tool-key" className="mb-1 block text-sm font-medium text-fg">
              Key
            </label>
            <input
              id="tool-key"
              type="text"
              value={key}
              onChange={(e) => {
                setKey(e.target.value);
                setKeyError("");
              }}
              disabled={isEditing}
              placeholder="brave-search"
              className={cn(INPUT_CLASS, isEditing && "opacity-60")}
            />
            {keyError.length > 0 && (
              <p className="mt-1 text-xs text-error">{keyError}</p>
            )}
          </div>
          <div>
            <label htmlFor="tool-name" className="mb-1 block text-sm font-medium text-fg">
              Name
            </label>
            <input
              id="tool-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="brave-search"
              className={INPUT_CLASS}
            />
          </div>
        </div>

        <div>
          <label htmlFor="tool-description" className="mb-1 block text-sm font-medium text-fg">
            Description
          </label>
          <textarea
            id="tool-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What this tool does..."
            rows={2}
            className={cn(INPUT_CLASS, "resize-none")}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="tool-mcp-tool" className="mb-1 block text-sm font-medium text-fg">
              MCP Server
            </label>
            {serverKeys.length > 0 ? (
              <select
                id="tool-mcp-tool"
                value={mcpTool}
                onChange={(e) => setMcpTool(e.target.value)}
                className={INPUT_CLASS}
              >
                <option value="">Select a server...</option>
                {serverKeys.map((k) => (
                  <option key={k} value={k}>
                    {k}
                  </option>
                ))}
              </select>
            ) : (
              <input
                id="tool-mcp-tool"
                type="text"
                value={mcpTool}
                onChange={(e) => setMcpTool(e.target.value)}
                placeholder="MCP server key"
                className={INPUT_CLASS}
              />
            )}
          </div>
          <div>
            <label htmlFor="tool-group" className="mb-1 block text-sm font-medium text-fg">
              Groups <span className="text-fg-subtle">(comma-separated)</span>
            </label>
            <input
              id="tool-group"
              type="text"
              value={group}
              onChange={(e) => setGroup(e.target.value)}
              placeholder="default"
              className={INPUT_CLASS}
            />
          </div>
        </div>

        {/* Arguments editor */}
        <div>
          <div className="mb-2 flex items-center justify-between">
            <label className="text-sm font-medium text-fg">Arguments</label>
            <button
              type="button"
              onClick={addArg}
              className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-brand-400 hover:bg-brand-600/10"
            >
              <Plus className="h-3 w-3" />
              Add
            </button>
          </div>
          {args.length === 0 && (
            <p className="text-xs text-fg-subtle">
              No arguments defined. Click "Add" to add one.
            </p>
          )}
          <div className="space-y-2">
            {args.map((arg, i) => (
              <div key={i} className="flex items-start gap-2">
                <input
                  type="text"
                  value={arg.name}
                  onChange={(e) => updateArg(i, "name", e.target.value)}
                  placeholder="name"
                  aria-label={`Argument ${i + 1} name`}
                  className="w-28 shrink-0 rounded-md border border-border bg-surface-100 px-2 py-1.5 text-xs text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none"
                />
                <select
                  value={arg.type}
                  onChange={(e) => updateArg(i, "type", e.target.value)}
                  aria-label={`Argument ${i + 1} type`}
                  className="w-24 shrink-0 rounded-md border border-border bg-surface-100 px-2 py-1.5 text-xs text-fg focus:border-brand-500 focus:outline-none"
                >
                  {ARG_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
                <input
                  type="text"
                  value={arg.description}
                  onChange={(e) => updateArg(i, "description", e.target.value)}
                  placeholder="description"
                  aria-label={`Argument ${i + 1} description`}
                  className="min-w-0 flex-1 rounded-md border border-border bg-surface-100 px-2 py-1.5 text-xs text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none"
                />
                <button
                  type="button"
                  onClick={() => removeArg(i)}
                  aria-label={`Remove argument ${i + 1}`}
                  className="shrink-0 rounded-md p-1.5 text-fg-subtle hover:bg-error/10 hover:text-error"
                >
                  <Trash2 className="h-3 w-3" />
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// DeleteConfirmDialog
// ---------------------------------------------------------------------------

function DeleteConfirmDialog({
  open,
  onClose,
  onConfirm,
  entityType,
  entityKey,
  warning,
}: {
  open: boolean;
  onClose: () => void;
  onConfirm: () => Promise<void>;
  entityType: string;
  entityKey: string;
  warning?: string;
}) {
  const [deleting, setDeleting] = useState(false);

  const handleConfirm = async () => {
    setDeleting(true);
    try {
      await onConfirm();
      onClose();
    } finally {
      setDeleting(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={`Delete ${entityType}`}
      footer={
        <>
          <button
            onClick={onClose}
            className="rounded-lg border border-border px-4 py-2 text-sm text-fg-muted hover:bg-surface-200"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={deleting}
            className="flex items-center gap-2 rounded-lg bg-error px-4 py-2 text-sm font-medium text-white hover:bg-error/80 disabled:opacity-40"
          >
            {deleting && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            Delete
          </button>
        </>
      }
    >
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-warning" />
        <div>
          <p className="text-sm text-fg">
            Are you sure you want to delete{" "}
            <span className="font-mono font-medium">{entityKey}</span>?
          </p>
          <p className="mt-1 text-xs text-fg-subtle">
            This action cannot be undone.
          </p>
          {warning && (
            <p className="mt-2 rounded-md bg-warning/10 px-3 py-2 text-xs text-warning">
              {warning}
            </p>
          )}
        </div>
      </div>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// ServerCard
// ---------------------------------------------------------------------------

function ServerCard({
  entry,
  onEdit,
  onDelete,
}: {
  entry: McpServerEntry;
  onEdit: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-border bg-surface-50 px-4 py-3">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <Server className="h-4 w-4 shrink-0 text-fg-subtle" />
          <span className="truncate font-mono text-sm font-medium text-fg">
            {entry.key}
          </span>
          {entry.config["auth-token"] && (
            <span title="Authenticated"><Lock className="h-3 w-3 shrink-0 text-fg-subtle" /></span>
          )}
        </div>
        <p className="mt-0.5 truncate pl-6 text-xs text-fg-muted">
          {entry.config.url}
        </p>
        {entry.config["remote-name"] && (
          <p className="mt-0.5 pl-6 text-xs text-fg-subtle">
            remote: {entry.config["remote-name"]}
          </p>
        )}
      </div>
      <div className="flex items-center gap-1">
        <button
          onClick={onEdit}
          aria-label={`Edit server ${entry.key}`}
          className="rounded-md p-1.5 text-fg-subtle hover:bg-surface-200 hover:text-fg"
        >
          <Pencil className="h-3.5 w-3.5" />
        </button>
        <button
          onClick={onDelete}
          aria-label={`Delete server ${entry.key}`}
          className="rounded-md p-1.5 text-fg-subtle hover:bg-error/10 hover:text-error"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// ToolCard
// ---------------------------------------------------------------------------

function ToolCard({
  entry,
  onEdit,
  onDelete,
}: {
  entry: ToolEntry;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const isMcp = entry.config.type === "mcp-tool";
  const argCount = entry.config.arguments?.length ?? 0;

  return (
    <div className="flex items-center justify-between rounded-lg border border-border bg-surface-50 px-4 py-3">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <Wrench className="h-4 w-4 shrink-0 text-fg-subtle" />
          <span className="truncate font-mono text-sm font-medium text-fg">
            {entry.config.name || entry.key}
          </span>
          <span
            className={cn(
              "shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium uppercase",
              isMcp
                ? "bg-brand-600/20 text-brand-400"
                : "bg-surface-200 text-fg-muted",
            )}
          >
            {isMcp ? "MCP" : entry.config.type}
          </span>
        </div>
        {entry.config.description && (
          <p className="mt-0.5 truncate pl-6 text-xs text-fg-muted">
            {entry.config.description}
          </p>
        )}
        <div className="mt-1 flex items-center gap-3 pl-6">
          {isMcp && entry.config["mcp-tool"] && (
            <span className="text-[10px] text-fg-subtle">
              server: {entry.config["mcp-tool"]}
            </span>
          )}
          {argCount > 0 && (
            <span className="text-[10px] text-fg-subtle">
              {argCount} arg{argCount !== 1 ? "s" : ""}
            </span>
          )}
          {entry.config.group && entry.config.group.length > 0 && (
            <span className="flex items-center gap-0.5 text-[10px] text-fg-subtle">
              <Tag className="h-2.5 w-2.5" />
              {entry.config.group.join(", ")}
            </span>
          )}
        </div>
      </div>
      {isMcp && (
        <div className="flex items-center gap-1">
          <button
            onClick={onEdit}
            aria-label={`Edit tool ${entry.key}`}
            className="rounded-md p-1.5 text-fg-subtle hover:bg-surface-200 hover:text-fg"
          >
            <Pencil className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={onDelete}
            aria-label={`Delete tool ${entry.key}`}
            className="rounded-md p-1.5 text-fg-subtle hover:bg-error/10 hover:text-error"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      )}
      {!isMcp && (
        <span className="shrink-0 text-[10px] text-fg-subtle">built-in</span>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// MCP Tools Page
// ---------------------------------------------------------------------------

export default function McpToolsPage() {
  const { featureSwitches } = useSettings((s) => s.settings);
  const notify = useNotification();
  const {
    servers,
    tools,
    loading,
    error,
    saveServer,
    deleteServer,
    saveTool,
    deleteTool,
    refresh,
  } = useMcpConfig();

  const [activeTab, setActiveTab] = useState<Tab>("servers");

  // Server dialog state
  const [serverDialogOpen, setServerDialogOpen] = useState(false);
  const [editingServer, setEditingServer] = useState<McpServerEntry | undefined>();

  // Tool dialog state
  const [toolDialogOpen, setToolDialogOpen] = useState(false);
  const [editingTool, setEditingTool] = useState<ToolEntry | undefined>();

  // Delete dialog state
  const [deleteTarget, setDeleteTarget] = useState<{
    type: "server" | "tool";
    key: string;
    warning?: string;
  } | null>(null);

  // Handlers
  const openAddServer = () => {
    setEditingServer(undefined);
    setServerDialogOpen(true);
  };

  const openEditServer = (entry: McpServerEntry) => {
    setEditingServer(entry);
    setServerDialogOpen(true);
  };

  const openDeleteServer = (key: string) => {
    const referencingTools = tools
      .filter((t) => t.config["mcp-tool"] === key)
      .map((t) => t.key);
    const warning =
      referencingTools.length > 0
        ? `The following tools reference this server and will stop working: ${referencingTools.join(", ")}`
        : undefined;
    setDeleteTarget({
      type: "server",
      key,
      ...(warning !== undefined ? { warning } : {}),
    });
  };

  const openAddTool = () => {
    setEditingTool(undefined);
    setToolDialogOpen(true);
  };

  const openEditTool = (entry: ToolEntry) => {
    setEditingTool(entry);
    setToolDialogOpen(true);
  };

  const openDeleteTool = (key: string) => {
    setDeleteTarget({ type: "tool", key });
  };

  const handleSaveServer = useCallback(
    async (key: string, config: McpServerConfig) => {
      await saveServer(key, config);
      notify.success("Server saved", `MCP server "${key}" has been saved.`);
    },
    [saveServer, notify],
  );

  const handleSaveTool = useCallback(
    async (key: string, config: ToolConfig) => {
      await saveTool(key, config);
      notify.success("Tool saved", `Tool "${key}" has been saved.`);
    },
    [saveTool, notify],
  );

  const handleDelete = useCallback(async () => {
    if (deleteTarget === null) return;
    try {
      if (deleteTarget.type === "server") {
        await deleteServer(deleteTarget.key);
        notify.success(
          "Server deleted",
          `MCP server "${deleteTarget.key}" has been deleted.`,
        );
      } else {
        await deleteTool(deleteTarget.key);
        notify.success(
          "Tool deleted",
          `Tool "${deleteTarget.key}" has been deleted.`,
        );
      }
    } catch (err) {
      notify.error(
        "Delete failed",
        err instanceof Error ? err.message : String(err),
      );
    }
    setDeleteTarget(null);
  }, [deleteTarget, deleteServer, deleteTool, notify]);

  // Feature flag gate
  if (!featureSwitches.mcpTools) {
    return (
      <div className="flex h-full flex-col items-center justify-center">
        <Plug className="mb-3 h-10 w-10 text-fg-subtle opacity-30" />
        <p className="text-fg-subtle">MCP Tools is not enabled.</p>
        <p className="mt-1 text-xs text-fg-subtle">
          Enable it in Settings → Feature Switches → MCP Tools.
        </p>
      </div>
    );
  }

  const mcpTools = tools.filter((t) => t.config.type === "mcp-tool");
  const nativeTools = tools.filter((t) => t.config.type !== "mcp-tool");
  const serverKeys = servers.map((s) => s.key);
  const toolKeys = tools.map((t) => t.key);

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <Plug className="h-6 w-6 text-brand-400" />
          <h1 className="text-2xl font-bold text-fg">MCP Tools</h1>
          <span className="ml-2 rounded bg-surface-200 px-2 py-0.5 text-xs text-fg-muted">
            {servers.length} server{servers.length !== 1 ? "s" : ""}, {mcpTools.length} tool{mcpTools.length !== 1 ? "s" : ""}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => refresh()}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-sm text-fg-muted transition-colors hover:bg-surface-200 disabled:opacity-40"
          >
            <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
            Refresh
          </button>
          <button
            onClick={activeTab === "servers" ? openAddServer : openAddTool}
            className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-500"
          >
            <Plus className="h-4 w-4" />
            {activeTab === "servers" ? "Add Server" : "Add Tool"}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div
        role="tablist"
        aria-label="MCP sections"
        className="mb-4 flex gap-1 rounded-lg bg-surface-100 p-1"
        onKeyDown={(e) => {
          const tabs: Tab[] = ["servers", "tools"];
          const idx = tabs.indexOf(activeTab);
          if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
            e.preventDefault();
            const next = e.key === "ArrowRight" ? (idx + 1) % tabs.length : (idx - 1 + tabs.length) % tabs.length;
            setActiveTab(tabs[next]);
            const el = document.getElementById(`tab-${tabs[next]}`);
            el?.focus();
          }
        }}
      >
        <button
          id="tab-servers"
          role="tab"
          aria-selected={activeTab === "servers"}
          aria-controls="panel-servers"
          tabIndex={activeTab === "servers" ? 0 : -1}
          onClick={() => setActiveTab("servers")}
          className={cn(
            "flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors",
            activeTab === "servers"
              ? "bg-surface-50 text-fg shadow-sm"
              : "text-fg-muted hover:text-fg",
          )}
        >
          <Server className="h-3.5 w-3.5" />
          Servers
        </button>
        <button
          id="tab-tools"
          role="tab"
          aria-selected={activeTab === "tools"}
          aria-controls="panel-tools"
          tabIndex={activeTab === "tools" ? 0 : -1}
          onClick={() => setActiveTab("tools")}
          className={cn(
            "flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors",
            activeTab === "tools"
              ? "bg-surface-50 text-fg shadow-sm"
              : "text-fg-muted hover:text-fg",
          )}
        >
          <Wrench className="h-3.5 w-3.5" />
          Tools
        </button>
      </div>

      {/* Error */}
      {error !== null && error.length > 0 && (
        <p role="alert" className="mb-4 rounded-lg bg-error/10 px-4 py-2 text-sm text-error">
          {error}
        </p>
      )}

      {/* Loading */}
      {loading && servers.length === 0 && tools.length === 0 && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="mr-2 h-5 w-5 animate-spin text-fg-subtle" />
          <span className="text-fg-subtle">Loading MCP configuration...</span>
        </div>
      )}

      {/* Servers tab */}
      {activeTab === "servers" && (
        <div id="panel-servers" role="tabpanel" aria-labelledby="tab-servers" tabIndex={0} className="flex flex-1 flex-col gap-2 overflow-y-auto">
          {!loading && servers.length === 0 && (
            <div className="flex flex-1 flex-col items-center justify-center">
              <Server className="mb-3 h-10 w-10 text-fg-subtle opacity-30" />
              <p className="text-fg-subtle">No MCP servers configured.</p>
              <p className="mt-1 text-xs text-fg-subtle">
                Click "Add Server" to connect an external MCP server.
              </p>
            </div>
          )}
          {servers.map((entry) => (
            <ServerCard
              key={entry.key}
              entry={entry}
              onEdit={() => openEditServer(entry)}
              onDelete={() => openDeleteServer(entry.key)}
            />
          ))}
        </div>
      )}

      {/* Tools tab */}
      {activeTab === "tools" && (
        <div id="panel-tools" role="tabpanel" aria-labelledby="tab-tools" tabIndex={0} className="flex flex-1 flex-col gap-2 overflow-y-auto">
          {!loading && tools.length === 0 && (
            <div className="flex flex-1 flex-col items-center justify-center">
              <Wrench className="mb-3 h-10 w-10 text-fg-subtle opacity-30" />
              <p className="text-fg-subtle">No tools configured.</p>
              <p className="mt-1 text-xs text-fg-subtle">
                Click "Add Tool" to create an MCP tool.
              </p>
            </div>
          )}
          {mcpTools.length > 0 && (
            <div className="space-y-2">
              <h2 className="text-xs font-medium uppercase tracking-wider text-fg-subtle">
                MCP Tools ({mcpTools.length})
              </h2>
              {mcpTools.map((entry) => (
                <ToolCard
                  key={entry.key}
                  entry={entry}
                  onEdit={() => openEditTool(entry)}
                  onDelete={() => openDeleteTool(entry.key)}
                />
              ))}
            </div>
          )}
          {nativeTools.length > 0 && (
            <div className="mt-4 space-y-2">
              <h2 className="text-xs font-medium uppercase tracking-wider text-fg-subtle">
                Built-in Tools ({nativeTools.length})
              </h2>
              {nativeTools.map((entry) => (
                <ToolCard
                  key={entry.key}
                  entry={entry}
                  onEdit={() => {}}
                  onDelete={() => {}}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Dialogs */}
      <McpServerDialog
        open={serverDialogOpen}
        onClose={() => setServerDialogOpen(false)}
        onSave={handleSaveServer}
        existingKeys={serverKeys}
        {...(editingServer !== undefined ? { initial: editingServer } : {})}
      />
      <McpToolDialog
        open={toolDialogOpen}
        onClose={() => setToolDialogOpen(false)}
        onSave={handleSaveTool}
        existingKeys={toolKeys}
        serverKeys={serverKeys}
        {...(editingTool !== undefined ? { initial: editingTool } : {})}
      />
      <DeleteConfirmDialog
        open={deleteTarget !== null}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
        entityType={deleteTarget?.type === "server" ? "MCP Server" : "Tool"}
        entityKey={deleteTarget?.key ?? ""}
        {...(deleteTarget?.warning !== undefined ? { warning: deleteTarget.warning } : {})}
      />
    </div>
  );
}
