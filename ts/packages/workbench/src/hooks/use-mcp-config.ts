import { useCallback, useEffect, useState } from "react";
import { useSocket } from "@/providers/socket-provider";
import { useConnectionState } from "@/providers/socket-provider";
import { useProgressStore } from "./use-progress-store";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface McpServerConfig {
  url: string;
  "remote-name"?: string;
  "auth-token"?: string;
}

export interface McpServerEntry {
  key: string;
  config: McpServerConfig;
}

export interface ToolArgument {
  name: string;
  type: string;
  description: string;
}

export interface ToolConfig {
  type: string;
  name: string;
  description: string;
  "mcp-tool"?: string;
  group?: string[];
  arguments?: ToolArgument[];
}

export interface ToolEntry {
  key: string;
  config: ToolConfig;
}

export interface UseMcpConfigReturn {
  servers: McpServerEntry[];
  tools: ToolEntry[];
  loading: boolean;
  error: string | null;

  loadServers: () => Promise<void>;
  saveServer: (key: string, config: McpServerConfig) => Promise<void>;
  deleteServer: (key: string) => Promise<void>;

  loadTools: () => Promise<void>;
  saveTool: (key: string, config: ToolConfig) => Promise<void>;
  deleteTool: (key: string) => Promise<void>;

  refresh: () => Promise<void>;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useMcpConfig(): UseMcpConfigReturn {
  const socket = useSocket();
  const connectionState = useConnectionState();
  const addActivity = useProgressStore((s) => s.addActivity);
  const removeActivity = useProgressStore((s) => s.removeActivity);

  const [servers, setServers] = useState<McpServerEntry[]>([]);
  const [tools, setTools] = useState<ToolEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadServers = useCallback(async () => {
    try {
      const raw = await socket.config().getValues("mcp");
      const entries: McpServerEntry[] = [];
      for (const item of raw as { key: string; value: string }[]) {
        try {
          entries.push({ key: item.key, config: JSON.parse(item.value) });
        } catch {
          console.warn(`[useMcpConfig] Failed to parse MCP server config: ${item.key}`);
        }
      }
      setServers(entries);
    } catch (err) {
      console.error("[useMcpConfig] loadServers error:", err);
      throw err;
    }
  }, [socket]);

  const loadTools = useCallback(async () => {
    try {
      const raw = await socket.config().getValues("tool");
      const entries: ToolEntry[] = [];
      for (const item of raw as { key: string; value: string }[]) {
        try {
          entries.push({ key: item.key, config: JSON.parse(item.value) });
        } catch {
          console.warn(`[useMcpConfig] Failed to parse tool config: ${item.key}`);
        }
      }
      setTools(entries);
    } catch (err) {
      console.error("[useMcpConfig] loadTools error:", err);
      throw err;
    }
  }, [socket]);

  const refresh = useCallback(async () => {
    const act = "Load MCP config";
    try {
      setLoading(true);
      setError(null);
      addActivity(act);
      await Promise.all([loadServers(), loadTools()]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
    } finally {
      setLoading(false);
      removeActivity(act);
    }
  }, [addActivity, removeActivity, loadServers, loadTools]);

  const saveServer = useCallback(
    async (key: string, config: McpServerConfig) => {
      const act = `Save MCP server ${key}`;
      try {
        addActivity(act);
        await socket
          .config()
          .putConfig([{ type: "mcp", key, value: JSON.stringify(config) }]);
        await loadServers();
      } finally {
        removeActivity(act);
      }
    },
    [socket, addActivity, removeActivity, loadServers],
  );

  const deleteServer = useCallback(
    async (key: string) => {
      const act = `Delete MCP server ${key}`;
      try {
        addActivity(act);
        await socket.config().deleteConfig({ type: "mcp", key });
        await loadServers();
      } finally {
        removeActivity(act);
      }
    },
    [socket, addActivity, removeActivity, loadServers],
  );

  const saveTool = useCallback(
    async (key: string, config: ToolConfig) => {
      const act = `Save tool ${key}`;
      try {
        addActivity(act);
        await socket
          .config()
          .putConfig([{ type: "tool", key, value: JSON.stringify(config) }]);
        await loadTools();
      } finally {
        removeActivity(act);
      }
    },
    [socket, addActivity, removeActivity, loadTools],
  );

  const deleteTool = useCallback(
    async (key: string) => {
      const act = `Delete tool ${key}`;
      try {
        addActivity(act);
        await socket.config().deleteConfig({ type: "tool", key });
        await loadTools();
      } finally {
        removeActivity(act);
      }
    },
    [socket, addActivity, removeActivity, loadTools],
  );

  // Auto-load when connection becomes ready
  useEffect(() => {
    if (
      connectionState.status === "connected" ||
      connectionState.status === "authenticated" ||
      connectionState.status === "unauthenticated"
    ) {
      refresh();
    }
  }, [connectionState.status, refresh]);

  return {
    servers,
    tools,
    loading,
    error,
    loadServers,
    saveServer,
    deleteServer,
    loadTools,
    saveTool,
    deleteTool,
    refresh,
  };
}
