// Flow Builder Module
// Processes flow blueprints and builds complete flow configurations
// Handles {blueprint}, {id}, and parameter substitutions

local param_processor = import "parameter-processor.jsonnet";

{
    // Builds blueprint-level processors with parameter substitution
    // Processes the 'blueprint' section of flow blueprints
    build_blueprint_processors: function(flow_blueprints, blueprint_name, parameters)
        [
            [
                // Replace {blueprint} in the processor key
                local key = std.strReplace(processor.key, "{blueprint}", blueprint_name);
                local parts = std.splitLimit(key, ":", 2);
                parts,
                {
                    // Process each field in the processor configuration
                    [field.key]:
                        // First replace {blueprint}, then substitute parameters
                        local blueprint_replaced = std.strReplace(field.value, "{blueprint}", blueprint_name);
                        param_processor.substitute_parameters(blueprint_replaced, parameters)
                    for field in std.objectKeysValuesAll(processor.value)
                }
            ]
            for processor in std.objectKeysValuesAll(flow_blueprints[blueprint_name].blueprint)
        ],

    // Builds flow-level processors with parameter substitution
    // Processes the 'flow' section of flow blueprints
    build_flow_processors: function(flow_blueprints, blueprint_name, flow_id, parameters)
        [
            [
                // Replace both {blueprint} and {id} in the processor key
                local key = std.strReplace(
                    std.strReplace(processor.key, "{blueprint}", blueprint_name),
                    "{id}", flow_id
                );
                local parts = std.splitLimit(key, ":", 2);
                parts,
                {
                    // Process each field in the processor configuration
                    [field.key]:
                        // Replace {blueprint} and {id}, then substitute parameters
                        local blueprint_replaced = std.strReplace(field.value, "{blueprint}", blueprint_name);
                        local id_replaced = std.strReplace(blueprint_replaced, "{id}", flow_id);
                        param_processor.substitute_parameters(id_replaced, parameters)
                    for field in std.objectKeysValuesAll(processor.value)
                }
            ]
            for processor in std.objectKeysValuesAll(flow_blueprints[blueprint_name].flow)
        ],

    // Combines blueprint and flow processors into flow objects
    build_flow_objects: function(processor_array)
        std.map(
            function(item) {
                [item[0][0]] +: {
                    [item[0][1]]: item[1]
                }
            },
            processor_array
        ),

    // Merges all flow objects into a single flows_active configuration
    merge_flow_objects: function(flow_objects)
        std.foldr(
            function(a, b) a + b,
            flow_objects,
            {}
        ),
}
