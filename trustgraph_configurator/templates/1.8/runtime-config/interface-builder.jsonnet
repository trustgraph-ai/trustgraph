// Interface Builder Module
// Processes flow class interfaces with parameter substitution
// Handles both string interfaces and nested object interfaces

local param_processor = import "parameter-processor.jsonnet";

{
    // Builds interfaces for a specific flow class and instance
    // Processes the 'interfaces' section of flow classes
    build_interfaces: function(flow_classes, class_name, flow_id, parameters)
        local interface_spec = flow_classes[class_name].interfaces;
        {
            [interface.key]:
                if std.isString(interface.value) then
                    // Simple string interface - apply all substitutions
                    local class_replaced = std.strReplace(interface.value, "{class}", class_name);
                    local id_replaced = std.strReplace(class_replaced, "{id}", flow_id);
                    param_processor.substitute_parameters(id_replaced, parameters)
                else
                    // Complex object interface - process nested fields
                    {
                        [field.key]:
                            local class_replaced = std.strReplace(field.value, "{class}", class_name);
                            local id_replaced = std.strReplace(class_replaced, "{id}", flow_id);
                            param_processor.substitute_parameters(id_replaced, parameters)
                        for field in std.objectKeysValuesAll(interface.value)
                    }
            for interface in std.objectKeysValuesAll(interface_spec)
        },
}