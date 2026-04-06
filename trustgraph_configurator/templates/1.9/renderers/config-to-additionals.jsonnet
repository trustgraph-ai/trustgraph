local decode = import "decode-config.jsonnet";

// Import config
local config = import "config.json";

// Produce patterns from config
local patterns = decode(config);

// Custom engine that collects configVolume parts
local engine = {

    // Collection of all configVolume parts
    configVolumes:: [],

    // Implement all required engine methods as no-ops
    container:: function(name) {
        with_image:: function(x) self,
        with_command:: function(x) self,
        with_environment:: function(x) self,
        with_limits:: function(c, m) self,
        with_reservations:: function(c, m) self,
        with_port:: function(src, dest, name) self,
        with_volume_mount:: function(vol, mnt) self,
        with_user:: function(x) self,
        with_runtime:: function(x) self,
        with_privileged:: function(x) self,
        with_ipc:: function(x) self,
        with_capability:: function(x) self,
        with_device:: function(hdev, cdev) self,
        with_env_var_secrets:: function(vars) self,
    },

    volume:: function(name) {
        with_size:: function(size) self,
    },

    // The key method - collects configVolume parts
    configVolume:: function(name, dir, parts)
        local collector = self + {
            configVolumes: super.configVolumes + [
                {
                    dir: dir,
                    parts: parts,
                }
            ]
        };
        {
            // Return a dummy volume that has the collector in it
            name: name,
            with_size:: function(size) collector,
            // Provide a way to get back to the collector
            getCollector:: function() collector,
        },

    secretVolume:: function(name, dir, parts) {
        with_size:: function(size) self,
    },

    envSecrets:: function(name) {
        with_env_var:: function(name, key) self,
    },

    containers:: function(name, containers) self,

    service:: function(containers) {
        with_port:: function(src, dest, name) self,
    },

    internalService:: function(containers) {
        with_port:: function(src, dest, name) self,
    },

    resources:: function(res)
        // Fold over resources and collect any configVolume state
        local collected = std.foldl(
            function(state, r)
                if std.objectHasAll(r, 'getCollector') then
                    // Merge the configVolumes from the volume's collector into our state
                    local volumeCollector = r.getCollector();
                    state + {
                        configVolumes: state.configVolumes + volumeCollector.configVolumes
                    }
                else
                    state,
            res,
            self
        );
        collected,
};

// Execute all component create() functions with our collecting engine
// Note: create:: is a hidden field, so we must use objectHasAll not objectHas
local result = std.foldl(
    function(state, p)
        if std.objectHasAll(p, 'create') then
            // Pattern has create directly - call it
            p.create(state)
        else
            state,
    std.objectValues(patterns),
    engine
);

// Debug: show what we collected
local debug = {
    numPatterns: std.length(std.objectValues(patterns)),
    numConfigVolumes: std.length(result.configVolumes),
};

// Transform collected data into output format
local allFiles = std.flattenArrays([
    [
        {
            // Remove trailing slash from dir to avoid double slashes
            path: std.join("/", [std.rstripChars(cv.dir, "/"), filename]),
            content: cv.parts[filename]
        }
        for filename in std.objectFields(cv.parts)
    ]
    for cv in result.configVolumes
]);

// Deduplicate by path - use a map to keep only unique paths
local uniqueMap = std.foldl(
    function(acc, item) acc + { [item.path]: item },
    allFiles,
    {}
);

// Convert back to array
local additionals = std.objectValues(uniqueMap);

// Output the array
additionals
