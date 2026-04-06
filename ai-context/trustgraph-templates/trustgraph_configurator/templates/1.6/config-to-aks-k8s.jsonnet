
local engine = import "engine/aks-k8s.jsonnet";
local decode = import "util/decode-config.jsonnet";
local components = import "components.jsonnet";

// Import config
local config = import "config.json";

// Produce patterns from config
local patterns = decode(config);

// Extract resources usnig the engine
local resourceList = engine.package(patterns);

resourceList

