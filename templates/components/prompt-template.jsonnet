local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";
local default_prompts = import "prompts/default-prompts.jsonnet";

{

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
                        "non-persistent://tg/response/text-completion-response",

                        "--system-prompt",
                        $["system-template"],

                        "--prompt",
                        "question={{question}}",
                        "extract-definitions=" +
                        $["prompt-definition-template"],
                        "extract-relationships=" +
                        $["prompt-relationship-template"],
                        "extract-topics=" +
                        $["prompt-topic-template"],
                        "kg-prompt=" +
                        $["prompt-knowledge-query-template"],
                        "document-prompt=" +
                        $["prompt-document-query-template"],
                        "extract-rows=" +
                        $["prompt-rows-template"],

                        "--prompt-response-type",
                        "extract-definitions=json",
                        "extract-relationships=json",
                        "extract-topics=json",
                        "kg-prompt=text",
                        "document-prompt=text",
                        "extract-rows=json",

                        "--prompt-schema",
                        'extract-definitions={ "type": "array", "items": { "type": "object", "properties": { "entity": { "type": "string" }, "definition": { "type": "string" } }, "required": [ "entity", "definition" ] } }',
                        'extract-relationships={ "type": "array", "items": { "type": "object", "properties": { "subject": { "type": "string" }, "predicate": { "type": "string" },  "object": { "type": "string" },  "object-entity": { "type": "boolean" } }, "required": [ "subject", "predicate", "object", "object-entity" ] } }',
                        'extract-topics={ "type": "array", "items": { "type": "object", "properties": { "topic": { "type": "string" }, "definition": { "type": "string" } }, "required": [ "topic", "definition" ] } }',

                    ])
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
                        "non-persistent://tg/response/prompt-rag-response",
                        "--text-completion-request-queue",
                        "non-persistent://tg/request/text-completion-rag",
                        "--text-completion-response-queue",
                        "non-persistent://tg/response/text-completion-rag-response",

                        "--system-prompt",
                        $["system-template"],

                        "--prompt",
                        "question={{question}}",
                        "extract-definitions=" +
                        $["prompt-definition-template"],
                        "extract-relationships=" +
                        $["prompt-relationship-template"],
                        "extract-topics=" +
                        $["prompt-topic-template"],
                        "kg-prompt=" +
                        $["prompt-knowledge-query-template"],
                        "document-prompt=" +
                        $["prompt-document-query-template"],
                        "extract-rows=" +
                        $["prompt-rows-template"],

                        "--prompt-response-type",
                        "extract-definitions=json",
                        "extract-relationships=json",
                        "extract-topics=json",
                        "kg-prompt=text",
                        "document-prompt=text",
                        "extract-rows=json",

                        "--prompt-schema",
                        'extract-definitions={ "type": "array", "items": { "type": "object", "properties": { "entity": { "type": "string" }, "definition": { "type": "string" } }, "required": [ "entity", "definition" ] } }',
                        'extract-relationships={ "type": "array", "items": { "type": "object", "properties": { "subject": { "type": "string" }, "predicate": { "type": "string" },  "object": { "type": "string" },  "object-entity": { "type": "boolean" } }, "required": [ "subject", "predicate", "object", "object-entity" ] } }',
                        'extract-topics={ "type": "array", "items": { "type": "object", "properties": { "topic": { "type": "string" }, "definition": { "type": "string" } }, "required": [ "topic", "definition" ] } }',

                    ])
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

