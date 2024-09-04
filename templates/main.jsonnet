
local engine = import "docker-compose.jsonnet";
local decode = import "decode-config.jsonnet";
local components = import "components.jsonnet";

// Options
local options = std.split(std.extVar("options"), ",");

// Produce patterns from config
local patterns = std.foldl(
    function(state, p) state + components[p],
    options,
    {}
);

// Extract resources usnig the engine
local resources = std.foldl(
    function(state, p) state + p.create(engine),
    std.objectValues(patterns),
    {}
);

std.manifestYamlDoc(resources)

