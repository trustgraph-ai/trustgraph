// Configuration Composer Module
// Orchestrates the complete configuration building process
// Combines all components into the final TrustGraph configuration

local flow_builder = import "flow-builder.jsonnet";
local interface_builder = import "interface-builder.jsonnet";

{
    // Main function to build the complete configuration
    build: function(config_spec)
        // Extract configuration parameters
        local flow_blueprints = config_spec.flow_blueprints;
        local default_flow_blueprint = config_spec.default_flow_blueprint;
        local default_flow_id = config_spec.default_flow_id;
        local flow_init_parameters = config_spec.flow_init_parameters;

        // Build all processors for the default flow
        local blueprint_processors = flow_builder.build_blueprint_processors(
            flow_blueprints,
            default_flow_blueprint,
            flow_init_parameters
        );

        local flow_processors = flow_builder.build_flow_processors(
            flow_blueprints,
            default_flow_blueprint,
            default_flow_id,
            flow_init_parameters
        );

        // Combine processors into flow objects
        local processor_array = blueprint_processors + flow_processors;
        local flow_objects = flow_builder.build_flow_objects(processor_array);
        local active_flows = flow_builder.merge_flow_objects(flow_objects);

        // Build interfaces for the default flow
        local default_flow_interfaces = interface_builder.build_interfaces(
            flow_blueprints,
            default_flow_blueprint,
            default_flow_id,
            flow_init_parameters
        );

        // Return object with nested configuration (for backwards compatibility)
        {
            // Create function (for backwards compatibility)
            create: function(engine) {},

            // The actual configuration object
            configuration: {
                // Prompts configuration
                prompt: {
                    "system": config_spec.prompts["system-template"],
                    "template-index": std.objectFieldsAll(config_spec.prompts.templates),
                } + {
                    ["template." + template.key]: template.value
                    for template in std.objectKeysValuesAll(config_spec.prompts.templates)
                },

                // Tools configuration
                tool: {
                    [tool.id]: tool
                    for tool in config_spec.tools
                },

                // MCP configuration
                mcp: config_spec.mcp,

                // Flow blueprints reference
                "flow-blueprint": flow_blueprints,

                // Interface descriptions
                "interface-description": config_spec.interface_descriptions,

                // Flow instances
                "flow": {
                    [default_flow_id]: {
                        "description": "Default processing flow",
                        "blueprint-name": default_flow_blueprint,
                        "interfaces": default_flow_interfaces,
                        "parameters": flow_init_parameters,
                    },
                },

                // Active flow processors
                "active-flow": active_flows,

                // Token costs and parameter types
                "token-cost": config_spec.token_costs,
                "parameter-type": config_spec.parameter_types,

                // Collections configuration
                "collection": config_spec.collection,

            },
        },
}
