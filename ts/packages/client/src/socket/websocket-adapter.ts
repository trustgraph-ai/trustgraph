/**
 * Isomorphic WebSocket adapter for browser and Node.js environments.
 *
 * In browsers, uses the native globalThis.WebSocket.
 * In Node.js, dynamically requires the 'ws' package.
 *
 * Provides its own minimal type definitions for the WebSocket API surface
 * we actually use, so the package does not require DOM lib types.
 */

// ---------------------------------------------------------------------------
// WebSocket readyState constants (identical in browser WebSocket and 'ws')
// ---------------------------------------------------------------------------
export const WS_CONNECTING = 0;
export const WS_OPEN = 1;
export const WS_CLOSING = 2;
export const WS_CLOSED = 3;

// ---------------------------------------------------------------------------
// Minimal WebSocket type surface used by this package
// ---------------------------------------------------------------------------

/** Minimal event type compatible with both browser Event and ws events. */
export interface WsEvent {
  type: string;
  [key: string]: unknown;
}

/** Minimal MessageEvent-compatible shape. */
export interface WsMessageEvent {
  data: unknown;
  type: string;
  [key: string]: unknown;
}

/** Minimal CloseEvent-compatible shape. */
export interface WsCloseEvent {
  code: number;
  reason: string;
  wasClean: boolean;
  type: string;
  [key: string]: unknown;
}

/**
 * Minimal interface covering the WebSocket instance methods and properties
 * used by this package.  Compatible with both browser `WebSocket` and the
 * `ws` npm package.
 */
export interface IsomorphicWebSocket {
  readonly readyState: number;
  send(data: string): void;
  close(code?: number, reason?: string): void;
  addEventListener(type: "message", listener: (event: WsMessageEvent) => void): void;
  addEventListener(type: "close", listener: (event: WsCloseEvent) => void): void;
  addEventListener(type: "open", listener: (event: WsEvent) => void): void;
  addEventListener(type: "error", listener: (event: WsEvent) => void): void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  removeEventListener(type: string, listener: (...args: any[]) => void): void;
}

/** Constructor signature for an isomorphic WebSocket implementation. */
export interface IsomorphicWebSocketConstructor {
  new (url: string): IsomorphicWebSocket;
}

// ---------------------------------------------------------------------------
// Runtime helpers
// ---------------------------------------------------------------------------

/**
 * Returns the WebSocket constructor appropriate for the current environment.
 *
 * - Browser: uses `globalThis.WebSocket` (native)
 * - Node.js: dynamically `require`s the `ws` npm package
 *
 * @throws Error if no WebSocket implementation is available
 */
export function getWebSocketConstructor(): IsomorphicWebSocketConstructor {
  // Browser environment (or Deno, Bun, etc. where WebSocket is global)
  if (typeof globalThis !== "undefined" && "WebSocket" in globalThis) {
    return (globalThis as unknown as { WebSocket: IsomorphicWebSocketConstructor }).WebSocket;
  }

  // Node.js environment — dynamically require 'ws'
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const ws = require("ws");
    return ws as IsomorphicWebSocketConstructor;
  } catch {
    throw new Error(
      'WebSocket is not available. In Node.js, install the "ws" package: npm install ws',
    );
  }
}

/**
 * Returns the default WebSocket URL for the current environment.
 *
 * - Browser: returns the relative path `"/api/v1/rpc"` (resolved by the
 *   browser against the current page origin).
 * - Node.js: returns a full URL `"ws://localhost:8088/api/v1/rpc"` since
 *   relative URLs are not meaningful outside a browser.
 */
export function getDefaultSocketUrl(): string {
  if (typeof window !== "undefined") {
    return "/api/v1/rpc";
  }
  return "ws://localhost:8088/api/v1/rpc";
}

/**
 * Isomorphic `getRandomValues` that works in both browser and Node.js.
 *
 * - Browser / Node.js 19+: uses `globalThis.crypto.getRandomValues`
 * - Older Node.js: falls back to `node:crypto.randomFillSync`
 */
export function getRandomValues(array: Uint32Array): Uint32Array {
  if (typeof globalThis.crypto?.getRandomValues === "function") {
    const random = globalThis.crypto.getRandomValues(new Uint32Array(array.length));
    array.set(random);
    return array;
  }
  // Node.js fallback for versions < 19 where globalThis.crypto may not exist
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { randomFillSync } = require("node:crypto");
    return randomFillSync(array) as Uint32Array;
  } catch {
    throw new Error(
      "No cryptographic random source available. " +
        "Upgrade to Node.js 19+ or ensure the 'crypto' module is available.",
    );
  }
}
