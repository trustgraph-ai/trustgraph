local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";

{

    "mcp-server-port":: 8000,

    "mcp-server" +: {
    
        create:: function(engine)

            local envSecrets = engine.envSecrets("mcp-server-secret")
                .with_env_var("MCP_SERVER_SECRET", "mcp-server-secret");

            local port = $["mcp-server-port"];

            local container =
                engine.container("mcp-server")
                    .with_image(images.trustgraph_mcp)
                    .with_command([
                        "mcp-server",
                        "--port",
                        std.toString(port),
                    ])
                    .with_env_var_secrets(envSecrets)
                    .with_limits("0.5", "256M")
                    .with_reservations("0.1", "256M")
                    .with_port(port, port, "mcp");

            local containerSet = engine.containers(
                "mcp-server", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(port, port, "mcp");

            engine.resources([
                envSecrets,
                containerSet,
                service,
            ])

    },

}

