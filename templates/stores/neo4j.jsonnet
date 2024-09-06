local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";

{

    "neo4j" +: {
    
        create:: function(engine)

            local vol = engine.volume("neo4j").with_size("20G");

            local container =
                engine.container("neo4j")
                    .with_image(images.neo4j)
                    .with_environment({
                        NEO4J_AUTH: "neo4j/password",
        //		NEO4J_server_bolt_listen__address: "0.0.0.0:7687",
        //		NEO4J_server_default__listen__address: "0.0.0.0",
        //		NEO4J_server_http_listen__address: "0.0.0.0:7474",
                    })
                    .with_limits("1.0", "768M")
                    .with_reservations("0.5", "768M")
                    .with_port(7474, 7474, "api")
                    .with_port(7687, 7687, "api2")
                    .with_volume_mount(vol, "/data");

            local containerSet = engine.containers(
                "neo4j", [ container ]
            );

            local service =
                engine.service(containerSet)
                .with_port(7474, 7474, "api")
                .with_port(7687, 7687, "api2);

            engine.resources([
                vol,
                containerSet,
                service,
           ])

    },

}

