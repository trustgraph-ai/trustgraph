local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";

{

    "mcp-server" +: {

        port:: 8000,
        "cpu-limit":: "0.5",
        "cpu-reservation":: "0.1",
        "memory-limit":: "256M",
        "memory-reservation":: "256M",

        create:: function(engine)

            local port = self.port;
            local memoryLimit = self["memory-limit"];
            local memoryReservation = self["memory-reservation"];

            local envSecrets = engine.envSecrets("mcp-server-secret")
                .with_env_var("MCP_SERVER_SECRET", "mcp-server-secret")
                .with_env_var("GATEWAY_SECRET", "gateway-secret");

            local container =
                engine.container("mcp-server")
                    .with_image(images.trustgraph_mcp)
                    .with_command([
                        "mcp-server",
                        "--port",
                        std.toString(port),
                    ])
                    .with_env_var_secrets(envSecrets)
                    .with_limits(self["cpu-limit"], memoryLimit)
                    .with_reservations(self["cpu-reservation"], memoryReservation)
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

