// @trustgraph/client
// TrustGraph TypeScript Client

// Export models (data types)
export * from "./models/Triple.js";
export * from "./models/messages.js";
export * from "./models/namespaces.js";

// Export socket client
export * from "./socket/trustgraph-socket.js";
export * from "./socket/effect-rpc-client.js";
export * from "./rpc/contract.js";

// Export WebSocket adapter (isomorphic helpers and types)
export * from "./socket/websocket-adapter.js";
