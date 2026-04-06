import { describe, it, expect, vi, beforeEach } from "vitest";
import { ServiceCall } from "../socket/service-call";

// Mock WebSocket constants
vi.stubGlobal("WebSocket", {
  OPEN: 1,
  CONNECTING: 0,
  CLOSING: 2,
  CLOSED: 3,
});

// Mock Socket interface
const mockSocket = {
  inflight: {} as Record<string, unknown>,
  ws: {
    send: vi.fn(),
    readyState: 1, // WebSocket.OPEN
  },
  reopen: vi.fn(),
};

// Mock setTimeout and clearTimeout
const mockSetTimeout = vi.fn();
const mockClearTimeout = vi.fn();

vi.stubGlobal("setTimeout", mockSetTimeout);
vi.stubGlobal("clearTimeout", mockClearTimeout);

describe("ServiceCall", () => {
  let mockSuccess: ReturnType<typeof vi.fn>;
  let mockError: ReturnType<typeof vi.fn>;
  let serviceCall: ServiceCall;

  beforeEach(() => {
    vi.clearAllMocks();
    mockSuccess = vi.fn();
    mockError = vi.fn();
    mockSocket.inflight = {} as Record<string, unknown>;
    mockSocket.ws = {
      send: vi.fn(),
      readyState: 1, // WebSocket.OPEN
    };
    mockSocket.reopen.mockClear();

    serviceCall = new ServiceCall(
      "test-mid",
      { id: "test-id", service: "test-service", request: { test: "data" } },
      mockSuccess,
      mockError,
      5000, // 5 second timeout
      3, // 3 retries
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      mockSocket as any,
    );
  });

  it("should initialize with correct properties", () => {
    expect(serviceCall.mid).toBe("test-mid");
    expect(serviceCall.timeout).toBe(5000);
    expect(serviceCall.retries).toBe(3);
    expect(serviceCall.complete).toBe(false);
    expect(serviceCall.socket).toBe(mockSocket);
  });

  it("should register itself in socket inflight when started", () => {
    serviceCall.start();

    expect(mockSocket.inflight["test-mid"]).toBe(serviceCall);
  });

  it("should send message on successful attempt", () => {
    serviceCall.start();

    expect(mockSocket.ws.send).toHaveBeenCalledWith(
      JSON.stringify({
        id: "test-id",
        service: "test-service",
        request: { test: "data" },
      }),
    );
    expect(mockSetTimeout).toHaveBeenCalled();
  });

  it("should handle successful response", () => {
    const responseData = { result: "success" };
    const message = { response: responseData };

    serviceCall.start();
    serviceCall.onReceived(message);

    expect(serviceCall.complete).toBe(true);
    expect(mockSuccess).toHaveBeenCalledWith(responseData);
    expect(mockClearTimeout).toHaveBeenCalled();
    expect(mockSocket.inflight["test-mid"]).toBeUndefined();
  });

  it("should handle timeout and retry", () => {
    serviceCall.start();

    // Initial retries should be 3, but start() calls attempt() which decrements to 2
    expect(serviceCall.retries).toBe(2);

    // Simulate timeout
    serviceCall.onTimeout();

    expect(mockClearTimeout).toHaveBeenCalled();
    expect(serviceCall.retries).toBe(1); // Should decrement from 2 to 1
  });

  it("should exhaust retries and call error callback", () => {
    // Set retries to 0 to force immediate failure
    serviceCall.retries = 0;

    serviceCall.start();

    expect(mockError).toHaveBeenCalledWith("Ran out of retries");
    expect(mockSocket.inflight["test-mid"]).toBeUndefined();
  });

  it("should handle WebSocket send failure", () => {
    mockSocket.ws.send.mockImplementation(() => {
      throw new Error("Connection failed");
    });

    serviceCall.start();

    // Should NOT call reopen anymore - BaseApi handles reconnection
    expect(mockSocket.reopen).not.toHaveBeenCalled();

    // With exponential backoff, the delay should be calculated as:
    // SOCKET_RECONNECTION_TIMEOUT * Math.pow(2, 3 - retries) + random
    // Since retries is decremented to 2 after start(), it's 3 - 2 = 1
    // So base delay is 2000 * 2^1 = 4000, plus random up to 1000
    // The delay should be between 4000 and 5000ms (capped at 30000)
    const callArgs = mockSetTimeout.mock.calls[0];
    expect(callArgs[0]).toEqual(expect.any(Function));
    expect(callArgs[1]).toBeGreaterThanOrEqual(4000);
    expect(callArgs[1]).toBeLessThanOrEqual(5000);
  });

  it("should handle missing WebSocket connection", () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (mockSocket as any).ws = null;

    serviceCall.start();

    // Should NOT trigger reopen - just wait for BaseApi to reconnect
    expect(mockSocket.reopen).not.toHaveBeenCalled();

    // Same calculation as above - base delay 4000ms + random up to 1000ms
    const callArgs = mockSetTimeout.mock.calls[0];
    expect(callArgs[0]).toEqual(expect.any(Function));
    expect(callArgs[1]).toBeGreaterThanOrEqual(4000);
    expect(callArgs[1]).toBeLessThanOrEqual(5000);
  });

  it("should not process response if already complete", () => {
    const consoleSpy = vi.spyOn(console, "log").mockImplementation(() => {});

    serviceCall.complete = true;
    serviceCall.onReceived({ result: "test" });

    expect(consoleSpy).toHaveBeenCalledWith(
      "test-mid",
      "should not happen, request is already complete",
    );

    consoleSpy.mockRestore();
  });

  it("should not timeout if already complete", () => {
    const consoleSpy = vi.spyOn(console, "log").mockImplementation(() => {});

    serviceCall.complete = true;
    serviceCall.onTimeout();

    expect(consoleSpy).toHaveBeenCalledWith(
      "test-mid",
      "timeout should not happen, request is already complete",
    );

    consoleSpy.mockRestore();
  });

  it("should not attempt if already complete", () => {
    const consoleSpy = vi.spyOn(console, "log").mockImplementation(() => {});

    serviceCall.complete = true;
    serviceCall.attempt();

    expect(consoleSpy).toHaveBeenCalledWith(
      "test-mid",
      "attempt should not be called, request is already complete",
    );

    consoleSpy.mockRestore();
  });

  it("should handle multiple retries correctly", () => {
    mockSocket.ws.send.mockImplementation(() => {
      throw new Error("Connection failed");
    });

    serviceCall.start();

    // Should have decremented retries and scheduled a retry
    expect(serviceCall.retries).toBe(2);
    // Should NOT call reopen - BaseApi handles reconnection
    expect(mockSocket.reopen).not.toHaveBeenCalled();
  });

  it("should clean up properly on successful response", () => {
    serviceCall.start();

    const responseData = { success: true };
    const message = { response: responseData };
    serviceCall.onReceived(message);

    expect(serviceCall.complete).toBe(true);
    expect(mockClearTimeout).toHaveBeenCalled();
    expect(mockSocket.inflight["test-mid"]).toBeUndefined();
    expect(mockSuccess).toHaveBeenCalledWith(responseData);
  });

  it("should handle edge case of negative retries", () => {
    serviceCall.retries = -1;

    serviceCall.attempt();

    expect(mockError).toHaveBeenCalledWith("Ran out of retries");
  });

  it("should bind timeout callbacks correctly", () => {
    serviceCall.start();

    // Verify that setTimeout was called with a bound function
    expect(mockSetTimeout).toHaveBeenCalledWith(expect.any(Function), 5000);
  });
});
