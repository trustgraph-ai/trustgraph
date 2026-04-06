local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";

// RabbitMQ messaging fabric configuration.
// Replaces Pulsar as the message broker for TrustGraph.

{

    "pub-sub-args":: [
        "--pubsub-backend",
        "rabbitmq",
        "--rabbitmq-host",
        "rabbitmq",
    ],

    "pub-sub-init-args":: [
        "--pulsar-admin-url",
        url.pulsar_admin,
    ],

    "overview-dashboard"::
        importstr "grafana/dashboards/overview-dashboard-rabbitmq.json",

    "prometheus-config"::
        importstr "prometheus/prometheus-rabbitmq.yml",

    "rabbitmq" +: {

        // Memory settings (can be overridden by memory-profile)
        "memory-limit":: "1024M",
        "memory-reservation":: "1024M",

        // CPU settings
        "cpu-limit":: "1",
        "cpu-reservation":: "0.1",

        create:: function(engine)

            local memoryLimit = self["memory-limit"];
            local memoryReservation = self["memory-reservation"];

            // RabbitMQ volume for persistent data
            local volume = engine.volume("rabbitmq").with_size("10G");

            // RabbitMQ container
            local container =
                engine.container("rabbitmq")
                    .with_image(images.rabbitmq)
                    .with_limits(self["cpu-limit"], memoryLimit)
                    .with_reservations(self["cpu-reservation"], memoryReservation)
                    .with_volume_mount(volume, "/var/lib/rabbitmq")
                    .with_environment({
                        "RABBITMQ_DEFAULT_USER": "guest",
                        "RABBITMQ_DEFAULT_PASS": "guest",
                    })
                    .with_port(5672, 5672, "amqp")
                    .with_port(15672, 15672, "management")
                    .with_port(15692, 15692, "metrics");

            local containerSet = engine.containers(
                "rabbitmq", [ container ]
            );

            // RabbitMQ service
            local service =
                engine.service(containerSet)
                .with_port(5672, 5672, "amqp")
                .with_port(15672, 15672, "management");

            engine.resources([
                volume,
                containerSet,
                service,
            ])

    }

}
