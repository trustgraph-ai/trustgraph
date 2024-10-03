
local engine = import "engine/docker-compose.jsonnet";
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
local resources = engine.package(patterns);

resources



