local images = import "values/images.jsonnet";

local config_initialiser = import "configuration.jsonnet";
local config  = import "../runtime-config/trustgraph-config.jsonnet";
local librarian = import "librarian.jsonnet";
local mcp_server = import "mcp-server.jsonnet";
local workbench = import "../ui/workbench-ui.jsonnet";
local graphrag = import "graph-rag.jsonnet";
local documentrag = import "document-rag.jsonnet";
local prompt_template = import "prompt-template.jsonnet";
local agent_manager = import "agent-orchestrator.jsonnet";
local structured_data = import "structured-data.jsonnet";
local ddg = import "mcp/ddg-mcp-server.jsonnet";

// Helper to create a routing function for a target object
local route = function(target)
    function(prefix, k, v)
        local suffix = std.substr(k, std.length(prefix), std.length(k) - std.length(prefix));
        { [target] +: { [suffix]:: v } };

// Parameter prefix -> target object routing table
local routes = {
    "prompt-rag-": route("prompt-rag"),
    "prompt-": route("prompt"),
    "text-completion-rag-": route("text-completion-rag"),
    "text-completion-": route("text-completion"),
    "embeddings-": route("embeddings"),
    "api-gateway-": route("api-gateway"),
    "chunk-": route("chunker"),
    "graph-rag-": route("graph-rag"),
    "graph-embeddings-": route("graph-embeddings"),
    "kg-extract-definitions-": route("kg-extract-definitions"),
    "kg-extract-relationships-": route("kg-extract-relationships"),
    "kg-extract-agent-": route("kg-extract-agent"),
    "kg-extract-ontology-": route("kg-extract-ontology"),
    "kg-extract-objects-": route("kg-extract-objects"),
    "garage-": route("garage"),
    "config-svc-": route("config-svc"),
    "document-decoder-": route("document-decoder"),
    "mcp-tool-": route("mcp-tool"),
    "mcp-server-": route("mcp-server"),
    "metering-rag-": route("metering-rag"),
    "metering-": route("metering"),
    "kg-store-": route("kg-store"),
    "kg-manager-": route("kg-manager"),
    "librarian-": route("librarian"),
    "agent-manager-": route("agent-manager"),
    "document-rag-": route("document-rag"),
    "document-embeddings-": route("document-embeddings"),
    "rev-gateway-": route("rev-gateway"),
    "nlp-query-": route("nlp-query"),
    "structured-query-": route("structured-query"),
    "structured-diag-": route("structured-diag"),
    "init-trustgraph-": route("init-trustgraph"),
};

// Find longest matching prefix (most specific first)
local findRoute = function(k)
    local prefixes = std.objectFields(routes);
    local matching = std.filter(function(p) std.startsWith(k, p), prefixes);
    local sorted = std.sort(matching, function(x) -std.length(x));
    if std.length(sorted) > 0 then sorted[0] else null;

{

    // Route parameters to appropriate internal objects based on prefix
    with:: function(k, v)
        local prefix = findRoute(k);
        if prefix != null then
            self + routes[prefix](prefix, k, v)
        else
            self + { [k]:: v },

    "log-level":: "INFO",

    // Base objects with concurrency defaults (LLM/embeddings components
    // merge into these)
    "text-completion" +: { concurrency:: 1 },
    "text-completion-rag" +: { concurrency:: 1 },
    embeddings +: { concurrency:: 1 },

    "api-gateway" +: {

        port:: 8088,
        timeout:: 600,
        "cpu-limit":: "0.5",
        "cpu-reservation":: "0.1",
        "memory-limit":: "512M",
        "memory-reservation":: "512M",

        create:: function(engine)

            local port = self.port;
            local timeout = self.timeout;
            local memoryLimit = self["memory-limit"];
            local memoryReservation = self["memory-reservation"];

            local envSecrets = engine.envSecrets("gateway-secret")
                .with_env_var("GATEWAY_SECRET", "gateway-secret");

            local container =
                engine.container("api-gateway")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "api-gateway",
                    ] + $["pub-sub-args"] + [
                        "--timeout",
                        std.toString(timeout),
                        "--port",
                        std.toString(port),
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_env_var_secrets(envSecrets)
                    .with_limits(self["cpu-limit"], memoryLimit)
                    .with_reservations(self["cpu-reservation"], memoryReservation)
                    .with_port(port, port, "api");

            local containerSet = engine.containers(
                "api-gateway", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics")
                .with_port(port, port, "api");

            engine.resources([
                envSecrets,
                containerSet,
                service,
            ])

    },

    "chunker" +: {

        size:: 2000,
        overlap:: 50,
        "cpu-limit":: "0.5",
        "cpu-reservation":: "0.1",
        "memory-limit":: "128M",
        "memory-reservation":: "128M",

        create:: function(engine)

            local size = self.size;
            local overlap = self.overlap;
            local memoryLimit = self["memory-limit"];
            local memoryReservation = self["memory-reservation"];

            local container =
                engine.container("chunker")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "chunker-recursive",
                    ] + $["pub-sub-args"] + [
                        "--chunk-size",
                        std.toString(size),
                        "--chunk-overlap",
                        std.toString(overlap),
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_limits(self["cpu-limit"], memoryLimit)
                    .with_reservations(self["cpu-reservation"], memoryReservation);

            local containerSet = engine.containers(
                "chunker", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "config-svc" +: {

        "cpu-limit":: "0.5",
        "cpu-reservation":: "0.1",
        "memory-limit":: "128M",
        "memory-reservation":: "128M",

        create:: function(engine)

            local cpuLimit = self["cpu-limit"];
            local cpuReservation = self["cpu-reservation"];
            local memoryLimit = self["memory-limit"];
            local memoryReservation = self["memory-reservation"];

            local container =
                engine.container("config-svc")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "config-svc",
                    ] + $["pub-sub-args"] + [
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_limits(cpuLimit, memoryLimit)
                    .with_reservations(cpuReservation, memoryReservation);

            local containerSet = engine.containers(
                "config-svc", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "document-decoder" +: {

        "cpu-limit":: "0.5",
        "cpu-reservation":: "0.1",
        "memory-limit":: "512M",
        "memory-reservation":: "512M",

        create:: function(engine)

            local memoryLimit = self["memory-limit"];
            local memoryReservation = self["memory-reservation"];

            local container =
                engine.container("document-decoder")
                    .with_image(images.trustgraph_unstructured)
                    .with_command([
                        "universal-decoder",
                    ] + $["pub-sub-args"] + [
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_limits(self["cpu-limit"], memoryLimit)
                    .with_reservations(self["cpu-reservation"], memoryReservation);

            local containerSet = engine.containers(
                "document-decoder", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "mcp-tool" +: {

        "cpu-limit":: "0.5",
        "cpu-reservation":: "0.1",
        "memory-limit":: "128M",
        "memory-reservation":: "128M",

        create:: function(engine)

            local memoryLimit = self["memory-limit"];
            local memoryReservation = self["memory-reservation"];

            local container =
                engine.container("mcp-tool")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "mcp-tool",
                    ] + $["pub-sub-args"] + [
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_limits(self["cpu-limit"], memoryLimit)
                    .with_reservations(self["cpu-reservation"], memoryReservation);

            local containerSet = engine.containers(
                "mcp-tool", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "metering" +: {

        "cpu-limit":: "0.5",
        "cpu-reservation":: "0.1",
        "memory-limit":: "128M",
        "memory-reservation":: "128M",

        create:: function(engine)

            local memoryLimit = self["memory-limit"];
            local memoryReservation = self["memory-reservation"];

            local container =
                engine.container("metering")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "metering",
                    ] + $["pub-sub-args"] + [
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_limits(self["cpu-limit"], memoryLimit)
                    .with_reservations(self["cpu-reservation"], memoryReservation);

            local containerSet = engine.containers(
                "metering", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "metering-rag" +: {

        "cpu-limit":: "0.5",
        "cpu-reservation":: "0.1",
        "memory-limit":: "128M",
        "memory-reservation":: "128M",

        create:: function(engine)

            local memoryLimit = self["memory-limit"];
            local memoryReservation = self["memory-reservation"];

            local container =
                engine.container("metering-rag")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "metering",
                    ] + $["pub-sub-args"] + [
                        "--id",
                        "metering-rag",
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_limits(self["cpu-limit"], memoryLimit)
                    .with_reservations(self["cpu-reservation"], memoryReservation);

            local containerSet = engine.containers(
                "metering-rag", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "kg-store" +: {

        "cpu-limit":: "0.5",
        "cpu-reservation":: "0.1",
        "memory-limit":: "128M",
        "memory-reservation":: "128M",

        create:: function(engine)

            local memoryLimit = self["memory-limit"];
            local memoryReservation = self["memory-reservation"];

            local container =
                engine.container("kg-store")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "kg-store",
                    ] + $["pub-sub-args"] + [
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_limits(self["cpu-limit"], memoryLimit)
                    .with_reservations(self["cpu-reservation"], memoryReservation);

            local containerSet = engine.containers(
                "kg-store", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                    .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "kg-manager" +: {

        "cpu-limit":: "0.5",
        "cpu-reservation":: "0.1",
        "memory-limit":: "128M",
        "memory-reservation":: "128M",

        create:: function(engine)

            local memoryLimit = self["memory-limit"];
            local memoryReservation = self["memory-reservation"];

            local container =
                engine.container("kg-manager")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "kg-manager",
                    ] + $["pub-sub-args"] + [
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_limits(self["cpu-limit"], memoryLimit)
                    .with_reservations(self["cpu-reservation"], memoryReservation);

            local containerSet = engine.containers(
                "kg-manager", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                    .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

} + librarian + mcp_server + workbench + graphrag
  + documentrag + prompt_template + agent_manager + structured_data
  + config_initialiser + config
  + ddg

