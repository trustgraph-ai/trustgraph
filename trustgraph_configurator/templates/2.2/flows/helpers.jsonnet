// Helper functions for flow configuration
// Provides utility functions for constructing flow, request, and response URIs
// used throughout the TrustGraph flow configuration system

// Creates a persistent flow URI for data streams
// Persistent flows retain messages until consumed
local flow(x) = "flow:tg:" + x;

// Creates a non-persistent request URI for request-response patterns
// Non-persistent means messages are not retained if no consumer is present
local request(x) = "request:tg:" + x;

// Creates a non-persistent response URI for request-response patterns
local response(x) = "response:tg:" + x;

// State broadcast queue — persistent, last-value semantics
local state(x) = "state:tg:" + x;

local librarian_request = request("librarian");
local librarian_response = request("librarian");

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
    state: state,
    librarian_request: librarian_request,
    librarian_response: librarian_response,
}

