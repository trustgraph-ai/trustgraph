// Helper functions for flow configuration
// Provides utility functions for constructing flow, request, and response URIs
// used throughout the TrustGraph flow configuration system

// Creates a persistent flow URI for data streams
// Persistent flows retain messages until consumed
local flow(x) = "persistent://tg/flow/" + x;

// Creates a non-persistent request URI for request-response patterns
// Non-persistent means messages are not retained if no consumer is present
local request(x) = "non-persistent://tg/request/" + x;

// Creates a non-persistent response URI for request-response patterns
local response(x) = "non-persistent://tg/response/" + x;

// Creates a request-response pair for bidirectional communication
// Returns an object with both request and response URIs
local request_response(x) = {
  request: request(x),
  response: response(x),
};

// Export all helper functions for use in other modules
{
    flow: flow,
    request: request,
    response: response,
    request_response: request_response,
}