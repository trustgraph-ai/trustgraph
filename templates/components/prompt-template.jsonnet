local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";
local default_prompts = import "prompts/default-prompts.jsonnet";

{

    prompts:: default_prompts,

    local prompt_template_args = [ "--prompt" ] + [
        p.key + "=" + p.value.prompt,
        for p in std.objectKeysValuesAll($.prompts.templates)
    ],

    local prompt_response_type_args = [ "--prompt-response-type" ] + [
        p.key + "=" + p.value["response-type"],
        for p in std.objectKeysValuesAll($.prompts.templates)
        if std.objectHas(p.value, "response-type")
    ],

    local prompt_schema_args = [ "--prompt-schema" ] + [
        (
            p.key + "=" +
            std.manifestJsonMinified(p.value["schema"])
        )
        for p in std.objectKeysValuesAll($.prompts.templates)
        if std.objectHas(p.value, "schema")
    ],

    local prompt_term_args = [ "--prompt-term" ] + [
        p.key + "=" + t.key + ":" + t.value
        for p in std.objectKeysValuesAll($.prompts.templates)
        if std.objectHas(p.value, "terms")
        for t in std.objectKeysValuesAll(p.value.terms)
    ],

    local prompt_args = prompt_template_args + prompt_response_type_args +
        prompt_schema_args + prompt_term_args,

    "prompt" +: {
    
        create:: function(engine)

            local container =
                engine.container("prompt")
                    .with_image(images.trustgraph)
                    .with_command([
                        "prompt-template",
                        "-p",
                        url.pulsar,

                        "--text-completion-request-queue",
                        "non-persistent://tg/request/text-completion",
                        "--text-completion-response-queue",
                        "non-persistent://tg/response/text-completion",

                        "--system-prompt",
                        $["prompts"]["system-template"],

                    ] + prompt_args
                    )
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "prompt", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8080, 8080, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "prompt-rag" +: {
    
        create:: function(engine)

            local container =
                engine.container("prompt-rag")
                    .with_image(images.trustgraph)
                    .with_command([
                        "prompt-template",
                        "-p",
                        url.pulsar,
                        "-i",
                        "non-persistent://tg/request/prompt-rag",
                        "-o",
                        "non-persistent://tg/response/prompt-rag",
                        "--text-completion-request-queue",
                        "non-persistent://tg/request/text-completion-rag",
                        "--text-completion-response-queue",
                        "non-persistent://tg/response/text-completion-rag",

                        "--system-prompt",
                        $["prompts"]["system-template"],

                    ] + prompt_args
                    )
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "prompt-rag", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8080, 8080, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

} + default_prompts

