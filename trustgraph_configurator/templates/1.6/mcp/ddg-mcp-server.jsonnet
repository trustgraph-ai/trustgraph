local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";

{

    "ddg-mcp-server-port":: 9870,

    "ddg-mcp-server" +: {

        create:: function(engine)

            local port = $["ddg-mcp-server-port"];

            local container =
                engine.container("ddg-mcp-server")
                    .with_image(images["ddg-mcp-server"])
                    .with_limits("0.5", "256M")
                    .with_reservations("0.1", "256M")
                    .with_port(port, port, "mcp");

            local containerSet = engine.containers(
                "ddg-mcp-server", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(port, port, "mcp");

            engine.resources([
                containerSet,
                service,
            ])

    },

    mcp +:: {
        "duckduckgo": {
            "remote-name": "search",
            local port = $["ddg-mcp-server-port"],
            local url = "http://ddg-mcp-server:%s/mcp" % port,
            "url": url,
        }

    },

}

