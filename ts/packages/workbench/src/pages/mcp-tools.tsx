import { useAtom, useAtomRefresh, useAtomSet, useAtomValue } from "@effect/atom-react";
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
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Dialog } from "@/components/ui/dialog";
import {
  deleteMcpServerAtom,
  deleteMcpToolAtom,
  mcpActiveTabAtom,
  mcpDeleteTargetAtom,
  mcpServerDialogAtom,
  mcpServerFormAtom,
  mcpServersAtom,
  mcpToolDialogAtom,
  mcpToolFormAtom,
  mcpToolsAtom,
  resultData,
  resultError,
  resultLoading,
  saveMcpServerAtom,
  saveMcpToolAtom,
  type McpServerEntry,
  type ToolEntry,
} from "@/atoms/workbench";

const INPUT_CLASS =
  "w-full rounded-lg border border-border bg-surface-100 px-4 py-2 text-sm text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500";
const ARG_TYPES = ["string", "number", "boolean", "object"] as const;

function ServerDialog({ existingKeys }: { existingKeys: string[] }) {
  const [dialog, setDialog] = useAtom(mcpServerDialogAtom);
  const [form, setForm] = useAtom(mcpServerFormAtom);
  const saveServer = useAtomSet(saveMcpServerAtom);
  const isEditing = dialog !== null && dialog !== "new";
  const open = dialog !== null;

  const close = () => {
    setDialog(null);
    setForm({ key: "", url: "", remoteName: "", authToken: "", showToken: false, saving: false, keyError: "" });
  };

  return (
    <Dialog
      open={open}
      onClose={close}
      title={isEditing ? "Edit MCP Server" : "Add MCP Server"}
      footer={
        <>
          <button onClick={close} className="rounded-lg border border-border px-4 py-2 text-sm text-fg-muted hover:bg-surface-200">
            Cancel
          </button>
          <button
            onClick={() => {
              const key = form.key.trim();
              if (key.length === 0 || form.url.trim().length === 0) return;
              if (!isEditing && existingKeys.includes(key)) {
                setForm({ ...form, keyError: "A server with this key already exists" });
                return;
              }
              saveServer({
                key,
                config: {
                  url: form.url.trim(),
                  ...(form.remoteName.trim().length > 0 ? { "remote-name": form.remoteName.trim() } : {}),
                  ...(form.authToken.trim().length > 0 ? { "auth-token": form.authToken.trim() } : {}),
                },
              });
              close();
            }}
            disabled={form.key.trim().length === 0 || form.url.trim().length === 0}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-500 disabled:opacity-40"
          >
            Save
          </button>
        </>
      }
    >
      <div className="space-y-4">
        <label className="block">
          <span className="mb-1 block text-sm font-medium text-fg">Key</span>
          <input
            value={form.key}
            onChange={(event) => setForm({ ...form, key: event.target.value, keyError: "" })}
            disabled={isEditing}
            placeholder="brave-search"
            className={cn(INPUT_CLASS, isEditing && "opacity-60")}
          />
          {form.keyError.length > 0 && <p className="mt-1 text-xs text-error">{form.keyError}</p>}
        </label>
        <label className="block">
          <span className="mb-1 block text-sm font-medium text-fg">URL</span>
          <input
            value={form.url}
            onChange={(event) => setForm({ ...form, url: event.target.value })}
            placeholder="http://localhost:8383/mcp"
            className={INPUT_CLASS}
          />
        </label>
        <label className="block">
          <span className="mb-1 block text-sm font-medium text-fg">Remote Name</span>
          <input
            value={form.remoteName}
            onChange={(event) => setForm({ ...form, remoteName: event.target.value })}
            placeholder="Optional tool name at the remote server"
            className={INPUT_CLASS}
          />
        </label>
        <label className="block">
          <span className="mb-1 block text-sm font-medium text-fg">Auth Token</span>
          <div className="relative">
            <input
              type={form.showToken ? "text" : "password"}
              value={form.authToken}
              onChange={(event) => setForm({ ...form, authToken: event.target.value })}
              placeholder="Bearer token"
              className={cn(INPUT_CLASS, "pr-10")}
            />
            <button
              type="button"
              onClick={() => setForm({ ...form, showToken: !form.showToken })}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-fg-subtle hover:text-fg"
              aria-label={form.showToken ? "Hide auth token" : "Show auth token"}
            >
              {form.showToken ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
        </label>
      </div>
    </Dialog>
  );
}

function ToolDialog({ serverKeys, existingKeys }: { serverKeys: string[]; existingKeys: string[] }) {
  const [dialog, setDialog] = useAtom(mcpToolDialogAtom);
  const [form, setForm] = useAtom(mcpToolFormAtom);
  const saveTool = useAtomSet(saveMcpToolAtom);
  const isEditing = dialog !== null && dialog !== "new";
  const open = dialog !== null;

  const close = () => {
    setDialog(null);
    setForm({ key: "", name: "", description: "", mcpTool: "", group: "default", args: [], saving: false, keyError: "" });
  };

  return (
    <Dialog
      open={open}
      onClose={close}
      title={isEditing ? "Edit MCP Tool" : "Add MCP Tool"}
      className="max-w-2xl"
      footer={
        <>
          <button onClick={close} className="rounded-lg border border-border px-4 py-2 text-sm text-fg-muted hover:bg-surface-200">
            Cancel
          </button>
          <button
            onClick={() => {
              const key = form.key.trim();
              if (key.length === 0 || form.name.trim().length === 0 || form.mcpTool.trim().length === 0) return;
              if (!isEditing && existingKeys.includes(key)) {
                setForm({ ...form, keyError: "A tool with this key already exists" });
                return;
              }
              saveTool({
                key,
                config: {
                  type: "mcp-tool",
                  name: form.name.trim(),
                  description: form.description.trim(),
                  "mcp-tool": form.mcpTool.trim(),
                  group: form.group.split(",").map((group) => group.trim()).filter((group) => group.length > 0),
                  arguments: form.args.filter((arg) => arg.name.trim().length > 0),
                },
              });
              close();
            }}
            disabled={form.key.trim().length === 0 || form.name.trim().length === 0 || form.mcpTool.trim().length === 0}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-500 disabled:opacity-40"
          >
            Save
          </button>
        </>
      }
    >
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-fg">Key</span>
            <input
              value={form.key}
              onChange={(event) => setForm({ ...form, key: event.target.value, keyError: "" })}
              disabled={isEditing}
              placeholder="brave-search"
              className={cn(INPUT_CLASS, isEditing && "opacity-60")}
            />
            {form.keyError.length > 0 && <p className="mt-1 text-xs text-error">{form.keyError}</p>}
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-fg">Name</span>
            <input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} className={INPUT_CLASS} />
          </label>
        </div>

        <label className="block">
          <span className="mb-1 block text-sm font-medium text-fg">Description</span>
          <textarea
            value={form.description}
            onChange={(event) => setForm({ ...form, description: event.target.value })}
            rows={2}
            className={cn(INPUT_CLASS, "resize-none")}
          />
        </label>

        <div className="grid grid-cols-2 gap-4">
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-fg">MCP Server</span>
            {serverKeys.length > 0 ? (
              <select value={form.mcpTool} onChange={(event) => setForm({ ...form, mcpTool: event.target.value })} className={INPUT_CLASS}>
                <option value="">Select a server...</option>
                {serverKeys.map((key) => <option key={key} value={key}>{key}</option>)}
              </select>
            ) : (
              <input value={form.mcpTool} onChange={(event) => setForm({ ...form, mcpTool: event.target.value })} className={INPUT_CLASS} />
            )}
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-fg">Groups</span>
            <input value={form.group} onChange={(event) => setForm({ ...form, group: event.target.value })} className={INPUT_CLASS} />
          </label>
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-medium text-fg">Arguments</span>
            <button
              type="button"
              onClick={() => setForm({ ...form, args: [...form.args, { name: "", type: "string", description: "" }] })}
              className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-brand-400 hover:bg-brand-600/10"
            >
              <Plus className="h-3 w-3" />
              Add
            </button>
          </div>
          <div className="space-y-2">
            {form.args.map((arg, index) => (
              <div key={index} className="flex items-start gap-2">
                <input
                  value={arg.name}
                  onChange={(event) => setForm({ ...form, args: form.args.map((item, i) => i === index ? { ...item, name: event.target.value } : item) })}
                  placeholder="name"
                  className="w-28 shrink-0 rounded-md border border-border bg-surface-100 px-2 py-1.5 text-xs text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none"
                />
                <select
                  value={arg.type}
                  onChange={(event) => setForm({ ...form, args: form.args.map((item, i) => i === index ? { ...item, type: event.target.value } : item) })}
                  className="w-24 shrink-0 rounded-md border border-border bg-surface-100 px-2 py-1.5 text-xs text-fg focus:border-brand-500 focus:outline-none"
                >
                  {ARG_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}
                </select>
                <input
                  value={arg.description}
                  onChange={(event) => setForm({ ...form, args: form.args.map((item, i) => i === index ? { ...item, description: event.target.value } : item) })}
                  placeholder="description"
                  className="min-w-0 flex-1 rounded-md border border-border bg-surface-100 px-2 py-1.5 text-xs text-fg placeholder:text-fg-subtle focus:border-brand-500 focus:outline-none"
                />
                <button
                  type="button"
                  onClick={() => setForm({ ...form, args: form.args.filter((_, i) => i !== index) })}
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

function ServerCard({ entry }: { entry: McpServerEntry }) {
  const setDialog = useAtomSet(mcpServerDialogAtom);
  const setForm = useAtomSet(mcpServerFormAtom);
  const setDeleteTarget = useAtomSet(mcpDeleteTargetAtom);
  return (
    <div className="flex items-center justify-between rounded-lg border border-border bg-surface-50 px-4 py-3">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <Server className="h-4 w-4 shrink-0 text-fg-subtle" />
          <span className="truncate font-mono text-sm font-medium text-fg">{entry.key}</span>
          {entry.config["auth-token"] && <Lock className="h-3 w-3 shrink-0 text-fg-subtle" />}
        </div>
        <p className="mt-0.5 truncate pl-6 text-xs text-fg-muted">{entry.config.url}</p>
      </div>
      <div className="flex items-center gap-1">
        <button
          onClick={() => {
            setForm({
              key: entry.key,
              url: entry.config.url,
              remoteName: entry.config["remote-name"] ?? "",
              authToken: entry.config["auth-token"] ?? "",
              showToken: false,
              saving: false,
              keyError: "",
            });
            setDialog(entry);
          }}
          aria-label={`Edit server ${entry.key}`}
          className="rounded-md p-1.5 text-fg-subtle hover:bg-surface-200 hover:text-fg"
        >
          <Pencil className="h-3.5 w-3.5" />
        </button>
        <button
          onClick={() => setDeleteTarget({ type: "server", key: entry.key })}
          aria-label={`Delete server ${entry.key}`}
          className="rounded-md p-1.5 text-fg-subtle hover:bg-error/10 hover:text-error"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}

function ToolCard({ entry }: { entry: ToolEntry }) {
  const setDialog = useAtomSet(mcpToolDialogAtom);
  const setForm = useAtomSet(mcpToolFormAtom);
  const setDeleteTarget = useAtomSet(mcpDeleteTargetAtom);
  return (
    <div className="rounded-lg border border-border bg-surface-50 px-4 py-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <Wrench className="h-4 w-4 shrink-0 text-fg-subtle" />
            <span className="truncate text-sm font-medium text-fg">{entry.config.name}</span>
          </div>
          <p className="mt-0.5 truncate pl-6 font-mono text-xs text-fg-subtle">{entry.key}</p>
          <p className="mt-0.5 pl-6 text-xs text-fg-muted">{entry.config.description}</p>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => {
              setForm({
                key: entry.key,
                name: entry.config.name,
                description: entry.config.description,
                mcpTool: entry.config["mcp-tool"] ?? "",
                group: entry.config.group?.join(", ") ?? "default",
                args: entry.config.arguments ?? [],
                saving: false,
                keyError: "",
              });
              setDialog(entry);
            }}
            aria-label={`Edit tool ${entry.key}`}
            className="rounded-md p-1.5 text-fg-subtle hover:bg-surface-200 hover:text-fg"
          >
            <Pencil className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => setDeleteTarget({ type: "tool", key: entry.key })}
            aria-label={`Delete tool ${entry.key}`}
            className="rounded-md p-1.5 text-fg-subtle hover:bg-error/10 hover:text-error"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}

export default function McpToolsPage() {
  const [activeTab, setActiveTab] = useAtom(mcpActiveTabAtom);
  const serversResult = useAtomValue(mcpServersAtom);
  const toolsResult = useAtomValue(mcpToolsAtom);
  const refreshServers = useAtomRefresh(mcpServersAtom);
  const refreshTools = useAtomRefresh(mcpToolsAtom);
  const servers = resultData(serversResult, []);
  const tools = resultData(toolsResult, []);
  const loading = resultLoading(serversResult, servers) || resultLoading(toolsResult, tools);
  const error = resultError(serversResult) ?? resultError(toolsResult);
  const setServerDialog = useAtomSet(mcpServerDialogAtom);
  const setToolDialog = useAtomSet(mcpToolDialogAtom);
  const [deleteTarget, setDeleteTarget] = useAtom(mcpDeleteTargetAtom);
  const deleteServer = useAtomSet(deleteMcpServerAtom);
  const deleteTool = useAtomSet(deleteMcpToolAtom);
  const serverKeys = servers.map((server) => server.key);

  const refresh = () => {
    refreshServers();
    refreshTools();
  };

  return (
    <div className="flex h-full flex-col">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <Plug className="h-6 w-6 text-brand-400" />
          <h1 className="text-2xl font-bold text-fg">MCP Tools</h1>
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

      <div className="mb-4 flex gap-1 rounded-lg bg-surface-100 p-1">
        {[
          ["servers", Server, `Servers (${servers.length})`] as const,
          ["tools", Wrench, `Tools (${tools.length})`] as const,
        ].map(([tab, Icon, label]) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              "flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors",
              activeTab === tab ? "bg-surface-50 text-fg shadow-sm" : "text-fg-muted hover:text-fg",
            )}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </button>
        ))}
      </div>

      {error !== null && (
        <p className="mb-4 rounded-lg bg-error/10 px-4 py-2 text-sm text-error">{error}</p>
      )}

      <div className="mb-4 flex justify-end">
        <button
          onClick={() => activeTab === "servers" ? setServerDialog("new") : setToolDialog("new")}
          className="flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-2 text-sm font-medium text-white hover:bg-brand-500"
        >
          <Plus className="h-3.5 w-3.5" />
          {activeTab === "servers" ? "Add Server" : "Add Tool"}
        </button>
      </div>

      {loading && servers.length === 0 && tools.length === 0 && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="mr-2 h-5 w-5 animate-spin text-fg-subtle" />
          <span className="text-fg-subtle">Loading MCP config...</span>
        </div>
      )}

      {activeTab === "servers" && (
        <div className="space-y-3">
          {servers.map((entry) => <ServerCard key={entry.key} entry={entry} />)}
          {!loading && servers.length === 0 && <p className="py-12 text-center text-fg-subtle">No MCP servers configured.</p>}
        </div>
      )}

      {activeTab === "tools" && (
        <div className="space-y-3">
          {tools.map((entry) => <ToolCard key={entry.key} entry={entry} />)}
          {!loading && tools.length === 0 && <p className="py-12 text-center text-fg-subtle">No MCP tools configured.</p>}
        </div>
      )}

      <ServerDialog existingKeys={serverKeys} />
      <ToolDialog serverKeys={serverKeys} existingKeys={tools.map((tool) => tool.key)} />

      <Dialog
        open={deleteTarget !== null}
        onClose={() => setDeleteTarget(null)}
        title={`Delete ${deleteTarget?.type ?? ""}`}
        footer={
          <>
            <button
              onClick={() => setDeleteTarget(null)}
              className="rounded-lg border border-border px-4 py-2 text-sm text-fg-muted hover:bg-surface-200"
            >
              Cancel
            </button>
            <button
              onClick={() => {
                if (deleteTarget?.type === "server") deleteServer(deleteTarget.key);
                if (deleteTarget?.type === "tool") deleteTool(deleteTarget.key);
                setDeleteTarget(null);
              }}
              className="rounded-lg bg-error px-4 py-2 text-sm font-medium text-white hover:opacity-90"
            >
              Delete
            </button>
          </>
        }
      >
        <div className="flex items-start gap-3">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-warning" />
          <p className="text-sm text-fg">
            Delete <span className="font-mono font-medium">{deleteTarget?.key}</span>?
          </p>
        </div>
      </Dialog>
    </div>
  );
}
