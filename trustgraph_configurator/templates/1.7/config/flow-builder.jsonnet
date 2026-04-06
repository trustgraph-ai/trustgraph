// Flow Builder Module
// Processes flow classes and builds complete flow configurations
// Handles {class}, {id}, and parameter substitutions

local param_processor = import "parameter-processor.jsonnet";

{
    // Builds class-level processors with parameter substitution
    // Processes the 'class' section of flow classes
    build_class_processors: function(flow_classes, class_name, parameters)
        [
            [
                // Replace {class} in the processor key
                local key = std.strReplace(processor.key, "{class}", class_name);
                local parts = std.splitLimit(key, ":", 2);
                parts,
                {
                    // Process each field in the processor configuration
                    [field.key]:
                        // First replace {class}, then substitute parameters
                        local class_replaced = std.strReplace(field.value, "{class}", class_name);
                        param_processor.substitute_parameters(class_replaced, parameters)
                    for field in std.objectKeysValuesAll(processor.value)
                }
            ]
            for processor in std.objectKeysValuesAll(flow_classes[class_name].class)
        ],

    // Builds flow-level processors with parameter substitution
    // Processes the 'flow' section of flow classes
    build_flow_processors: function(flow_classes, class_name, flow_id, parameters)
        [
            [
                // Replace both {class} and {id} in the processor key
                local key = std.strReplace(
                    std.strReplace(processor.key, "{class}", class_name),
                    "{id}", flow_id
                );
                local parts = std.splitLimit(key, ":", 2);
                parts,
                {
                    // Process each field in the processor configuration
                    [field.key]:
                        // Replace {class} and {id}, then substitute parameters
                        local class_replaced = std.strReplace(field.value, "{class}", class_name);
                        local id_replaced = std.strReplace(class_replaced, "{id}", flow_id);
                        param_processor.substitute_parameters(id_replaced, parameters)
                    for field in std.objectKeysValuesAll(processor.value)
                }
            ]
            for processor in std.objectKeysValuesAll(flow_classes[class_name].flow)
        ],

    // Combines class and flow processors into flow objects
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