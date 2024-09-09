
local engine = import "engine/minikube-k8s.jsonnet";
local decode = import "util/decode-config.jsonnet";
local components = import "components.jsonnet";

// Import config
local config = import "config.json";

// Produce patterns from config
local patterns = decode(config);

local ns = {
    apiVersion: "v1",
    kind: "Namespace",
    metadata: {
        name: "trustgraph",
    },
    "spec": {
    },
};

// Extract resources using the engine
local resourceList = engine.package(patterns);

resourceList

