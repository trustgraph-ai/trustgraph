import { RequestMessage } from "../models/messages";

// Constant defining the delay before attempting to reconnect a WebSocket
// (2 seconds)
export const SOCKET_RECONNECTION_TIMEOUT = 2000;

// Forward declare Socket type to avoid circular dependency
// Using a minimal interface that matches what BaseApi provides
interface Socket {
  ws?: WebSocket;
  inflight: { [key: string]: ServiceCall };
  reopen: () => void;
  getNextId?: () => string;
  user?: string;
}

/**
 * ServiceCall represents a single request/response cycle over a WebSocket
 * connection with built-in retry logic, timeout handling, and completion
 * tracking.
 *
 * This class manages the lifecycle of a service call including:
 * - Sending the initial request
 * - Handling timeouts and retries
 * - Managing completion state
 * - Cleaning up resources
 */
export class ServiceCall {
  constructor(
    mid: string, // Message ID - unique identifier for this request
    msg: RequestMessage, // The actual message/request to send
    success: (resp: unknown) => void, // Callback function called on
    // successful response
    error: (err: object | string) => void, // Callback function called on error/failure
    timeout: number, // Timeout duration in milliseconds
    retries: number, // Number of retry attempts allowed
    socket: Socket, // WebSocket instance to send the message through
  ) {
    this.mid = mid;
    this.msg = msg;
    this.success = success;
    this.error = error;
    this.timeout = timeout;
    this.retries = retries;
    this.socket = socket;
    this.complete = false; // Track if this request has completed
  }

  // Properties
  mid: string; // Message identifier
  msg: RequestMessage; // The request message
  success: (resp: unknown) => void; // Success callback
  error: (err: object | string) => void; // Error callback
  timeoutId?: ReturnType<typeof setTimeout>; // Reference to the active timeout timer
  timeout: number; // Timeout duration in milliseconds
  retries: number; // Remaining retry attempts
  socket: Socket; // WebSocket connection reference
  complete: boolean; // Flag indicating if request is complete

  /**
   * Initiates the service call by registering it with the socket's inflight
   * requests and making the first attempt to send the message
   */
  start() {
    // Register this request as "in-flight" so responses can be matched to it
    this.socket.inflight[this.mid] = this;
    // Make the first attempt to send the message
    this.attempt();
  }

  /**
   * Called when a response is received for this request
   * Handles cleanup and calls the success or error callback based on response
   *
   * @param resp - The response object received from the server
   */
  onReceived(resp: object) {
    // Defensive check - this shouldn't happen but log if it does
    if (this.complete == true)
      console.log(this.mid, "should not happen, request is already complete");

    // Mark as complete to prevent duplicate processing
    this.complete = true;

    // Clean up timeout timer
    clearTimeout(this.timeoutId);
    this.timeoutId = undefined;

    // Remove from inflight requests tracker
    delete this.socket.inflight[this.mid];

    // Check if the response contains an error (error can be directly in resp or nested under response)
    let errorToHandle: unknown = null;

    // Check for direct error in response
    if (resp && typeof resp === "object" && "error" in resp) {
      errorToHandle = (resp as Record<string, unknown>).error;
    }
    // Check for nested error under response property
    else if (resp && typeof resp === "object" && "response" in resp) {
      const response = (resp as Record<string, unknown>).response;
      if (response && typeof response === "object" && "error" in response) {
        errorToHandle = (response as Record<string, unknown>).error;
      }
    }

    if (errorToHandle) {
      // Response contains an error - call error callback
      const errorObj = errorToHandle as Record<string, unknown>;
      const errorMessage =
        (typeof errorObj.message === "string" ? errorObj.message : null) ||
        (typeof errorObj.type === "string" ? errorObj.type : null) ||
        "Unknown error";
      console.log(
        "ServiceCall: API error detected in response:",
        errorMessage,
        "Full error:",
        errorToHandle,
      );
      this.error(new Error(errorMessage));
      return;
    }

    // Extract the response field from the message object
    // The resp parameter is the full message: {id, response, complete}
    // We need to pass just the response field to the success callback
    const responseData = (resp as { response?: unknown }).response;
    this.success(responseData);
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

  /**
   * Called when the request times out
   * Triggers another attempt if retries are available
   */
  onTimeout() {
    // Defensive check - this shouldn't happen but log if it does
    if (this.complete == true)
      console.log(
        this.mid,
        "timeout should not happen, request is already complete",
      );

    console.log("Request", this.mid, "timed out");

    // Clear the current timeout
    clearTimeout(this.timeoutId);

    // Try again (this will check retry count)
    this.attempt();
  }

  /**
   * Calculates exponential backoff delay with jitter
   * @returns backoff delay in milliseconds
   */
  calculateBackoff() {
    return Math.min(
      SOCKET_RECONNECTION_TIMEOUT * Math.pow(2, 3 - this.retries) +
        Math.random() * 1000,
      30000, // Max 30 seconds
    );
  }

  /**
   * Core retry logic - attempts to send the message over the WebSocket
   * Handles retries and waits for BaseApi to handle reconnection
   */
  attempt() {
    // Defensive check - this shouldn't be called on completed requests
    if (this.complete == true)
      console.log(
        this.mid,
        "attempt should not be called, request is already complete",
      );

    // Decrement retry counter
    this.retries--;

    // Check if we've exhausted all retries
    if (this.retries < 0) {
      console.log("Request", this.mid, "ran out of retries");

      // Clean up and call error callback
      clearTimeout(this.timeoutId);
      delete this.socket.inflight[this.mid];
      this.error("Ran out of retries");
      return; // Exit early - no more attempts
    }

    // Check if WebSocket connection is available and ready
    if (this.socket.ws && this.socket.ws.readyState === WebSocket.OPEN) {
      try {
        // Attempt to send the message as JSON
        this.socket.ws.send(JSON.stringify(this.msg));

        // Set up timeout for this attempt
        this.timeoutId = setTimeout(this.onTimeout.bind(this), this.timeout);

        return; // Success - message sent, waiting for response or timeout
      } catch (e) {
        // Handle send failure - wait for BaseApi to handle reconnection
        console.log("Error:", e);
        console.log(
          "Message send failure, waiting for socket reconnection...",
        );

        // Schedule retry with backoff - let BaseApi handle the reconnection
        this.timeoutId = setTimeout(
          this.attempt.bind(this),
          this.calculateBackoff(),
        );
      }
    } else {
      // No WebSocket connection available or not ready
      // Let BaseApi handle reconnection, just wait and retry
      console.log("Request", this.mid, "waiting for socket reconnection...");

      // Use consistent backoff for all waiting scenarios
      setTimeout(this.attempt.bind(this), this.calculateBackoff());
    }
  }
}
