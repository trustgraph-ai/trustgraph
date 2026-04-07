import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import { BaseApi, type ConnectionState } from "@trustgraph/client";

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

interface SocketContextValue {
  api: BaseApi;
}

const SocketContext = createContext<SocketContextValue | null>(null);

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export interface SocketProviderProps {
  /** Username sent with every API request */
  user: string;
  /** Optional API key for authenticated connections */
  apiKey?: string;
  /** WebSocket URL (defaults to "/api/socket", proxied by Vite in dev) */
  socketUrl?: string;
  children: ReactNode;
}

/**
 * SocketProvider creates a single BaseApi instance that lives for the
 * lifetime of the provider and tears down the WebSocket on unmount.
 *
 * The BaseApi is recreated if `user`, `apiKey`, or `socketUrl` change.
 */
export function SocketProvider({
  user,
  apiKey,
  socketUrl,
  children,
}: SocketProviderProps) {
  const apiRef = useRef<BaseApi | null>(null);

  // Re-create the API instance when connection parameters change.
  // We track a serial number so downstream consumers re-render.
  const [serial, setSerial] = useState(0);

  useEffect(() => {
    // Close the previous socket if it exists
    apiRef.current?.close();

    const api = new BaseApi(user, apiKey, socketUrl);
    apiRef.current = api;
    setSerial((s) => s + 1);

    return () => {
      api.close();
      if (apiRef.current === api) {
        apiRef.current = null;
      }
    };
  }, [user, apiKey, socketUrl]);

  // Don't render children until the first API instance is ready
  if (!apiRef.current) return null;

  return (
    <SocketContext.Provider
      // eslint-disable-next-line react/no-children-prop
      key={serial}
      value={{ api: apiRef.current }}
    >
      {children}
    </SocketContext.Provider>
  );
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

/**
 * Returns the shared BaseApi instance.
 *
 * Must be called inside a `<SocketProvider>`.
 */
export function useSocket(): BaseApi {
  const ctx = useContext(SocketContext);
  if (!ctx) {
    throw new Error("useSocket must be used within a <SocketProvider>");
  }
  return ctx.api;
}

/**
 * Subscribes to connection-state changes emitted by BaseApi.
 *
 * Uses `useSyncExternalStore` for tear-free reads.
 */
export function useConnectionState(): ConnectionState {
  const api = useSocket();

  // We store the latest snapshot in a ref so the getSnapshot function is stable.
  const stateRef = useRef<ConnectionState>({
    status: "connecting",
    hasApiKey: false,
  });

  // subscribe must be stable across renders to prevent useSyncExternalStore
  // from re-subscribing on every render (which would cause an infinite loop
  // because onConnectionStateChange immediately calls the listener).
  const subscribe = useCallback(
    (onStoreChange: () => void) => {
      return api.onConnectionStateChange((next) => {
        stateRef.current = next;
        onStoreChange();
      });
    },
    [api],
  );

  const getSnapshot = useCallback(() => stateRef.current, []);

  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}
