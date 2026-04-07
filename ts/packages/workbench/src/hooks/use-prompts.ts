import { useCallback, useEffect, useState } from "react";
import { useSocket } from "@/providers/socket-provider";
import { useConnectionState } from "@/providers/socket-provider";

export function usePrompts() {
  const socket = useSocket();
  const connectionState = useConnectionState();
  const [prompts, setPrompts] = useState<Array<{ id: string; name?: string; description?: string }>>([]);
  const [systemPrompt, setSystemPrompt] = useState<string>("");
  const [loading, setLoading] = useState(false);

  const loadPrompts = useCallback(async () => {
    try {
      setLoading(true);
      const list = await socket.config().getPrompts();
      setPrompts(Array.isArray(list) ? list : []);
    } catch (err) {
      console.error("Failed to load prompts:", err);
    } finally {
      setLoading(false);
    }
  }, [socket]);

  const loadSystemPrompt = useCallback(async () => {
    try {
      const sp = await socket.config().getSystemPrompt();
      setSystemPrompt(typeof sp === "string" ? sp : JSON.stringify(sp, null, 2));
    } catch (err) {
      console.error("Failed to load system prompt:", err);
    }
  }, [socket]);

  const getPrompt = useCallback(async (id: string) => {
    return socket.config().getPrompt(id);
  }, [socket]);

  // Auto-load when connected
  useEffect(() => {
    const connected =
      connectionState.status === "connected" ||
      connectionState.status === "authenticated" ||
      connectionState.status === "unauthenticated";
    if (connected) {
      loadPrompts();
      loadSystemPrompt();
    }
  }, [connectionState.status, loadPrompts, loadSystemPrompt]);

  return { prompts, systemPrompt, loading, loadPrompts, loadSystemPrompt, getPrompt };
}
