import { afterEach, describe, expect, it, vi } from "vitest";
import {
  getRandomValues as fillRandomValues,
  getWebSocketConstructor,
  WebSocketAdapterError,
  WS_OPEN,
} from "../socket/websocket-adapter.js";

class FakeWebSocket {
  readonly readyState = WS_OPEN;

  constructor(readonly url: string) {}

  send(_data: string): void {}

  close(_code?: number, _reason?: string): void {}

  addEventListener(_type: string, _listener: (event: { readonly type: string }) => void): void {}

  removeEventListener(_type: string, _listener: (event: { readonly type: string }) => void): void {}
}

describe("websocket adapter", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("prefers a compatible global WebSocket constructor", () => {
    vi.stubGlobal("WebSocket", FakeWebSocket);

    const Constructor = getWebSocketConstructor();
    const socket = new Constructor("ws://example.test/rpc");

    expect(socket).toBeInstanceOf(FakeWebSocket);
    expect(socket.readyState).toBe(WS_OPEN);
  });

  it("loads the optional ws constructor when no global WebSocket exists", () => {
    vi.stubGlobal("WebSocket", undefined);

    expect(getWebSocketConstructor()).toBeTypeOf("function");
  });

  it("uses global crypto when available", () => {
    const getRandomValues = vi.fn((target: Uint32Array) => {
      target[0] = 42;
      return target;
    });
    vi.stubGlobal("crypto", { getRandomValues });

    const values = fillRandomValues(new Uint32Array(1));

    expect(values[0]).toBe(42);
    expect(getRandomValues).toHaveBeenCalledOnce();
  });

  it("raises a typed error when no crypto source is available", () => {
    vi.stubGlobal("crypto", undefined);

    expect(() => fillRandomValues(new Uint32Array(2))).toThrow(WebSocketAdapterError);
  });

  it("exposes typed adapter errors", () => {
    const error = WebSocketAdapterError.make({
      operation: "test",
      message: "typed",
    });

    expect(error._tag).toBe("WebSocketAdapterError");
    expect(error.message).toBe("typed");
  });
});
