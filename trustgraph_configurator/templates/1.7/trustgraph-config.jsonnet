// TrustGraph Main Configuration
// Clean, modular composition of TrustGraph configuration
// Uses specialized modules for different aspects of config building

// Import dependencies
local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";
local default_prompts = import "prompts/default-prompts.jsonnet";
local token_costs = import "values/token-costs.jsonnet";
local flow_classes = import "flows/flow-classes.jsonnet";
local config_composer = import "config/config-composer.jsonnet";
local interface_descriptions = import "config/interface-descriptions.jsonnet";
local tools = import "config/tools.jsonnet";
local temperature_params = import "parameters/temperature-param-types.jsonnet";
local chunking_params = import "parameters/chunking-param-types.jsonnet";

// Main configuration object
local configuration = {

    // Prompt templates
    prompts:: default_prompts,

    // Tool definitions
    tools:: tools,

    // MCP configuration
    mcp:: {},

    // Flow classes reference
    "flow-classes":: flow_classes,

    // LLM model parameters
    "llm-models" +:: {},

    // Embeddings model parameters
    "embeddings-models" +:: {},

    collections +:: {
      "trustgraph:default": {
        "user": "default-user",
        "collection": "default",
        "name": "Default Collection",
        "description": "Default collection",
        "tags": ["default"],
      },
    },

    // Default model and flow parameters
    flow_init_parameters:: {
        "llm-model": $["llm-models"].default,
        "llm-rag-model": $["llm-models"].default,
        "llm-temperature": "%0.3f" % $["parameter-types"]["llm-temperature"].default,
        "llm-rag-temperature": "%0.3f" % $["parameter-types"]["llm-temperature"].default,
        "chunk-size": std.toString($["parameter-types"]["chunk-size"].default),
        "chunk-overlap": std.toString($["parameter-types"]["chunk-overlap"].default),
        "embeddings-model": $["embeddings-models"].default,
    },

    // Interface descriptions for external endpoints
    "interface-descriptions":: interface_descriptions,

    // Parameter type definitions
    "parameter-types":: {
        "llm-model": $["llm-models"],
        "embeddings-model": $["embeddings-models"],
    } + chunking_params + temperature_params,

    // Token costs
    "token-costs":: token_costs,

    // Build the complete configuration using the composer
    configuration:: config_composer.build({
        flow_classes: $["flow-classes"],
        default_flow_class: "everything",
        default_flow_id: "default",
        flow_init_parameters: $["flow_init_parameters"],
        prompts: $["prompts"],
        tools: $["tools"],
        mcp: $["mcp"],
        interface_descriptions: $["interface-descriptions"],
        parameter_types: $["parameter-types"],
        token_costs: $["token-costs"],
        collection: $["collections"],
    }),

} + default_prompts;

// Export the final configuration
configuration
