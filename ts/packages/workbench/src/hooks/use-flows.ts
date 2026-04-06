import { useCallback, useEffect, useState } from "react";
import { useSocket } from "@/providers/socket-provider";
import { useConnectionState } from "@/providers/socket-provider";
import { useProgressStore } from "./use-progress-store";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface FlowSummary {
  id: string;
  description?: string;
  [key: string]: unknown;
}

export interface UseFlowsReturn {
  flows: FlowSummary[];
  loading: boolean;
  error: string | null;

  /** Refresh the flow list from the server */
  getFlows: () => Promise<void>;
  /** Start a new flow */
  startFlow: (
    id: string,
    blueprintName: string,
    description: string,
    parameters?: Record<string, unknown>,
  ) => Promise<void>;
  /** Stop a running flow */
  stopFlow: (id: string) => Promise<void>;
  /** Fetch a single flow definition */
  getFlow: (id: string) => Promise<FlowSummary>;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useFlows(): UseFlowsReturn {
  const socket = useSocket();
  const connectionState = useConnectionState();
  const addActivity = useProgressStore((s) => s.addActivity);
  const removeActivity = useProgressStore((s) => s.removeActivity);

  const [flows, setFlows] = useState<FlowSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getFlows = useCallback(async () => {
    const act = "Load flows";
    try {
      setLoading(true);
      setError(null);
      addActivity(act);

      const ids: string[] = await socket.flows().getFlows();
      const results = await Promise.all(
        ids.map(async (id) => {
          const def = await socket.flows().getFlow(id);
          return { id, ...def } as FlowSummary;
        }),
      );

      setFlows(results);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
      console.error("useFlows.getFlows error:", err);
    } finally {
      setLoading(false);
      removeActivity(act);
    }
  }, [socket, addActivity, removeActivity]);

  const startFlow = useCallback(
    async (
      id: string,
      blueprintName: string,
      description: string,
      parameters?: Record<string, unknown>,
    ) => {
      const act = `Start flow ${id}`;
      try {
        addActivity(act);
        await socket.flows().startFlow(id, blueprintName, description, parameters);
        // Refresh list after starting
        await getFlows();
      } finally {
        removeActivity(act);
      }
    },
    [socket, addActivity, removeActivity, getFlows],
  );

  const stopFlow = useCallback(
    async (id: string) => {
      const act = `Stop flow ${id}`;
      try {
        addActivity(act);
        await socket.flows().stopFlow(id);
        await getFlows();
      } finally {
        removeActivity(act);
      }
    },
    [socket, addActivity, removeActivity, getFlows],
  );

  const getFlow = useCallback(
    async (id: string): Promise<FlowSummary> => {
      const def = await socket.flows().getFlow(id);
      return { id, ...def } as FlowSummary;
    },
    [socket],
  );

  // Auto-load flows when the connection becomes ready
  useEffect(() => {
    if (
      connectionState.status === "connected" ||
      connectionState.status === "authenticated" ||
      connectionState.status === "unauthenticated"
    ) {
      getFlows();
    }
  }, [connectionState.status, getFlows]);

  return { flows, loading, error, getFlows, startFlow, stopFlow, getFlow };
}
