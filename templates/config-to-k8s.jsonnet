
local engine = import "k8s.jsonnet";
local decode = import "decode-config.jsonnet";
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

// Extract resources usnig the engine
local resources = std.foldl(
    function(state, p) state + p.create(engine),
    std.objectValues(patterns),
    {}
);

local resourceList = {
    apiVersion: "v1",
    kind: "List",
    items: [ns] + std.objectValues(resources.resources),
};

std.manifestYamlDoc(resourceList, quote_keys=false)
