local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";
local default_prompts = import "prompts/default-prompts.jsonnet";

{

    tools:: [],

    "agent-manager" +: {
    
        create:: function(engine)

            local container =
                engine.container("agent-manager")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "agent-manager-react",
                        "-p",
                        url.pulsar,
                        "--prompt-request-queue",
                        "non-persistent://tg/request/prompt-rag",
                        "--prompt-response-queue",
                        "non-persistent://tg/response/prompt-rag",
                        "--tool-type",
                    ] + [
                        tool.id + "=" + tool.type
                        for tool in $.tools
                    ] + [
                        "--tool-description"
                    ] + [
                        tool.id + "=" + tool.description
                        for tool in $.tools
                    ] + [
                        "--tool-argument"
                    ] + [
                        "%s=%s:%s:%s" % [
                            tool.id, arg.name, arg.type, arg.description
                        ]
                        for tool in $.tools
                        for arg in tool.arguments
                    ]
                    )
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "agent-manager", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

} + default_prompts

