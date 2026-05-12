import type { RequestMessage } from "../models/messages.js";
import { WS_OPEN, WS_CONNECTING, type IsomorphicWebSocket } from "./websocket-adapter.js";

// Constant defining the delay before attempting to reconnect a WebSocket
// (2 seconds)
export const SOCKET_RECONNECTION_TIMEOUT = 2000;

// Forward declare Socket type to avoid circular dependency
// Using a minimal interface that matches what BaseApi provides
interface Socket {
  ws: IsomorphicWebSocket | null | undefined;
  inflight: {
    [key: string]: {
      onReceived: (resp: object) => void;
      retryNow: () => void;
      error: (err: object | string) => void;
    };
  };
  reopen: () => void;
  getNextId?: () => string;
  user?: string;
}

export class ServiceCallMulti {
  constructor(
    mid: string,
    msg: RequestMessage,
    success: (resp: unknown) => void,
    error: (err: object | string) => void,
    timeout: number,
    retries: number,
    socket: Socket,
    receiver: (resp: unknown) => boolean,
  ) {
    this.mid = mid;
    this.msg = msg;
    this.success = success;
    this.error = error;
    this.timeout = timeout;
    this.retries = retries;
    this.socket = socket;
    this.complete = false;
    this.receiver = receiver;
  }

  mid: string;
  msg: RequestMessage;
  success: (resp: unknown) => void;
  error: (err: object | string) => void;
  receiver: (resp: unknown) => boolean;
  timeoutId: ReturnType<typeof setTimeout> | undefined = undefined;
  timeout: number;
  retries: number;
  socket: Socket;
  complete: boolean;

  start() {
    this.socket.inflight[this.mid] = this;
    this.attempt();
  }

  onReceived(resp: object) {
    if (this.complete == true)
      console.log(this.mid, "should not happen, request is already complete");

    const fin = this.receiver(resp);

    if (fin) {
      this.complete = true;

      //        console.log("Received for", this.mid);
      clearTimeout(this.timeoutId);
      this.timeoutId = undefined;
      delete this.socket.inflight[this.mid];
      this.success(resp);
    }
  }

  /**
   * Called when socket connects - immediately retry if we were waiting
   */
  retryNow() {
    if (this.complete) return;

    // Clear any pending backoff timer
    clearTimeout(this.timeoutId);
    this.timeoutId = undefined;

    // Restore retry count since we didn't actually fail
    this.retries++;

    // Attempt immediately
    this.attempt();
  }

  onTimeout() {
    if (this.complete == true)
      console.log(
        this.mid,
        "timeout should not happen, request is already complete",
      );

    console.log("Request", this.mid, "timed out");
    clearTimeout(this.timeoutId);
    this.attempt();
  }

  attempt() {
    //        console.log("attempt:", this.mid);

    if (this.complete == true)
      console.log(
        this.mid,
        "attempt should not be called, request is already complete",
      );

    this.retries--;

    if (this.retries < 0) {
      console.log("Request", this.mid, "ran out of retries");

      clearTimeout(this.timeoutId);
      delete this.socket.inflight[this.mid];

      this.error("Ran out of retries");
      return; // Exit early - no more attempts
    }

    // Check if WebSocket connection is available and ready
    if (this.socket.ws !== null && this.socket.ws !== undefined && this.socket.ws.readyState === WS_OPEN) {
      try {
        this.socket.ws.send(JSON.stringify(this.msg));
        this.timeoutId = setTimeout(this.onTimeout.bind(this), this.timeout);

        return;
      } catch (e) {
        console.log("Error:", e);
        console.log("Message send failure, retry...");

        // Calculate backoff delay with jitter
        const backoffDelay = Math.min(
          SOCKET_RECONNECTION_TIMEOUT * Math.pow(2, 3 - this.retries) +
            Math.random() * 1000,
          30000, // Max 30 seconds
        );

        this.timeoutId = setTimeout(this.attempt.bind(this), backoffDelay);

        console.log("Reopen...");
        // Attempt to reopen the WebSocket connection
        this.socket.reopen();
      }
    } else {
      // No WebSocket connection available or not ready
      // Check if socket is connecting
      if (
        this.socket.ws !== null &&
        this.socket.ws !== undefined &&
        this.socket.ws.readyState === WS_CONNECTING
      ) {
        // Wait a bit longer for connection to establish
        setTimeout(this.attempt.bind(this), 500);
      } else {
        // Socket is closed or closing, trigger reopen
        console.log("Socket not ready, reopening...");
        this.socket.reopen();

        // Calculate backoff delay
        const backoffDelay = Math.min(
          SOCKET_RECONNECTION_TIMEOUT * Math.pow(2, 3 - this.retries) +
            Math.random() * 1000,
          30000,
        );

        setTimeout(this.attempt.bind(this), backoffDelay);
      }
    }
  }
}
