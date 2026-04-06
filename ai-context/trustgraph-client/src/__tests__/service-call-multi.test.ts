import { describe, it, expect, vi, beforeEach } from "vitest";
import { ServiceCallMulti } from "../socket/service-call-multi";

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

describe("ServiceCallMulti", () => {
  let mockSuccess: ReturnType<typeof vi.fn>;
  let mockError: ReturnType<typeof vi.fn>;
  let mockReceiver: ReturnType<typeof vi.fn>;
  let serviceCallMulti: ServiceCallMulti;

  beforeEach(() => {
    vi.clearAllMocks();
    mockSuccess = vi.fn();
    mockError = vi.fn();
    mockReceiver = vi.fn();
    mockSocket.inflight = {} as Record<string, unknown>;
    mockSocket.ws = {
      send: vi.fn(),
      readyState: 1, // WebSocket.OPEN
    };
    mockSocket.reopen.mockClear();

    serviceCallMulti = new ServiceCallMulti(
      "test-mid",
      { id: "test-id", service: "test-service", request: { test: "data" } },
      mockSuccess,
      mockError,
      5000, // 5 second timeout
      3, // 3 retries
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      mockSocket as any,
      mockReceiver,
    );
  });

  it("should initialize with correct properties", () => {
    expect(serviceCallMulti.mid).toBe("test-mid");
    expect(serviceCallMulti.timeout).toBe(5000);
    expect(serviceCallMulti.retries).toBe(3);
    expect(serviceCallMulti.complete).toBe(false);
    expect(serviceCallMulti.socket).toBe(mockSocket);
    expect(serviceCallMulti.receiver).toBe(mockReceiver);
  });

  it("should register itself in socket inflight when started", () => {
    serviceCallMulti.start();

    expect(mockSocket.inflight["test-mid"]).toBe(serviceCallMulti);
  });

  it("should send message on successful attempt", () => {
    serviceCallMulti.start();

    expect(mockSocket.ws.send).toHaveBeenCalledWith(
      JSON.stringify({
        id: "test-id",
        service: "test-service",
        request: { test: "data" },
      }),
    );
    expect(mockSetTimeout).toHaveBeenCalled();
  });

  it("should handle response when receiver returns true (completion)", () => {
    mockReceiver.mockReturnValue(true); // Signal completion
    const response = { result: "success" };

    serviceCallMulti.start();
    serviceCallMulti.onReceived(response);

    expect(mockReceiver).toHaveBeenCalledWith(response);
    expect(serviceCallMulti.complete).toBe(true);
    expect(mockSuccess).toHaveBeenCalledWith(response);
    expect(mockClearTimeout).toHaveBeenCalled();
    expect(mockSocket.inflight["test-mid"]).toBeUndefined();
  });

  it("should handle response when receiver returns false (continue)", () => {
    mockReceiver.mockReturnValue(false); // Signal to continue
    const response = { partial: "data" };

    serviceCallMulti.start();
    serviceCallMulti.onReceived(response);

    expect(mockReceiver).toHaveBeenCalledWith(response);
    expect(serviceCallMulti.complete).toBe(false);
    expect(mockSuccess).not.toHaveBeenCalled();
    expect(mockClearTimeout).not.toHaveBeenCalled();
    expect(mockSocket.inflight["test-mid"]).toBe(serviceCallMulti);
  });

  it("should handle timeout and retry", () => {
    serviceCallMulti.start();

    // Initial retries should be 3, but start() calls attempt() which decrements to 2
    expect(serviceCallMulti.retries).toBe(2);

    // Simulate timeout
    serviceCallMulti.onTimeout();

    expect(mockClearTimeout).toHaveBeenCalled();
    expect(serviceCallMulti.retries).toBe(1); // Should decrement from 2 to 1
  });

  it("should exhaust retries and call error callback", () => {
    // Set retries to 0 to force immediate failure
    serviceCallMulti.retries = 0;

    serviceCallMulti.start();

    expect(mockError).toHaveBeenCalledWith("Ran out of retries");
    expect(mockSocket.inflight["test-mid"]).toBeUndefined();
  });

  it("should handle WebSocket send failure", () => {
    mockSocket.ws.send.mockImplementation(() => {
      throw new Error("Connection failed");
    });

    serviceCallMulti.start();

    expect(mockSocket.reopen).toHaveBeenCalled();

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

    serviceCallMulti.start();

    // Should trigger reopen and schedule with exponential backoff
    expect(mockSocket.reopen).toHaveBeenCalled();

    // Same calculation as above - base delay 4000ms + random up to 1000ms
    const callArgs = mockSetTimeout.mock.calls[0];
    expect(callArgs[0]).toEqual(expect.any(Function));
    expect(callArgs[1]).toBeGreaterThanOrEqual(4000);
    expect(callArgs[1]).toBeLessThanOrEqual(5000);
  });

  it("should not process response if already complete", () => {
    const consoleSpy = vi.spyOn(console, "log").mockImplementation(() => {});

    serviceCallMulti.complete = true;
    serviceCallMulti.onReceived({ result: "test" });

    expect(consoleSpy).toHaveBeenCalledWith(
      "test-mid",
      "should not happen, request is already complete",
    );

    consoleSpy.mockRestore();
  });

  it("should not timeout if already complete", () => {
    const consoleSpy = vi.spyOn(console, "log").mockImplementation(() => {});

    serviceCallMulti.complete = true;
    serviceCallMulti.onTimeout();

    expect(consoleSpy).toHaveBeenCalledWith(
      "test-mid",
      "timeout should not happen, request is already complete",
    );

    consoleSpy.mockRestore();
  });

  it("should not attempt if already complete", () => {
    const consoleSpy = vi.spyOn(console, "log").mockImplementation(() => {});

    serviceCallMulti.complete = true;
    serviceCallMulti.attempt();

    expect(consoleSpy).toHaveBeenCalledWith(
      "test-mid",
      "attempt should not be called, request is already complete",
    );

    consoleSpy.mockRestore();
  });

  it("should handle streaming responses correctly", () => {
    mockReceiver
      .mockReturnValueOnce(false) // First response - continue
      .mockReturnValueOnce(false) // Second response - continue
      .mockReturnValueOnce(true); // Third response - complete

    serviceCallMulti.start();

    // First response
    serviceCallMulti.onReceived({ chunk: 1 });
    expect(serviceCallMulti.complete).toBe(false);
    expect(mockSuccess).not.toHaveBeenCalled();

    // Second response
    serviceCallMulti.onReceived({ chunk: 2 });
    expect(serviceCallMulti.complete).toBe(false);
    expect(mockSuccess).not.toHaveBeenCalled();

    // Third response (final)
    serviceCallMulti.onReceived({ chunk: 3, final: true });
    expect(serviceCallMulti.complete).toBe(true);
    expect(mockSuccess).toHaveBeenCalledWith({ chunk: 3, final: true });
  });

  it("should handle receiver function errors gracefully", () => {
    mockReceiver.mockImplementation(() => {
      throw new Error("Receiver error");
    });

    serviceCallMulti.start();

    expect(() => {
      serviceCallMulti.onReceived({ test: "data" });
    }).toThrow("Receiver error");
  });

  it("should handle multiple timeout scenarios", () => {
    const consoleSpy = vi.spyOn(console, "log").mockImplementation(() => {});

    serviceCallMulti.start();

    // After start, retries should be 2 (decremented from 3)
    expect(serviceCallMulti.retries).toBe(2);

    // First timeout
    serviceCallMulti.onTimeout();
    expect(serviceCallMulti.retries).toBe(1);

    // Second timeout
    serviceCallMulti.onTimeout();
    expect(serviceCallMulti.retries).toBe(0);

    consoleSpy.mockRestore();
  });

  it("should clean up properly when receiver signals completion", () => {
    mockReceiver.mockReturnValue(true);

    serviceCallMulti.start();

    const response = { final: true };
    serviceCallMulti.onReceived(response);

    expect(serviceCallMulti.complete).toBe(true);
    expect(mockClearTimeout).toHaveBeenCalled();
    expect(mockSocket.inflight["test-mid"]).toBeUndefined();
    expect(mockSuccess).toHaveBeenCalledWith(response);
  });
});
