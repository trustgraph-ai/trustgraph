local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";

// This is a Pulsar configuration.  Non-standalone mode so we deploy
// individual components: bookkeeper, broker and zookeeper.
// 
// This also deploys the TrustGraph 'admin' container which initialises
// TrustGraph-specific namespaces etc.

{

    "pulsar" +: {

        create:: function(engine)

            // Zookeeper volume
            local zkVolume = engine.volume("zookeeper").with_size("1G");

            // Zookeeper container
            local zkContainer = 
                engine.container("zookeeper")
                    .with_image(images.pulsar)
                    .with_command([
                        "bash",
                        "-c",
                        "bin/apply-config-from-env.py conf/zookeeper.conf && bin/generate-zookeeper-config.sh conf/zookeeper.conf && exec bin/pulsar zookeeper"
                    ])
                    .with_limits("0.1", "400M")
                    .with_reservations("0.05", "400M")
                    .with_volume_mount(zkVolume, "/pulsar/data/zookeeper")
                    .with_environment({
                        "metadataStoreUrl": "zk:zookeeper:2181",
                        "PULSAR_MEM": "-Xms256m -Xmx256m -XX:MaxDirectMemorySize=256m",
                    })
                    .with_port(2181, 2181, "zookeeper")
                    .with_port(2888, 2888, "zookeeper2")
                    .with_port(3888, 3888, "zookeeper3");

            // Pulsar cluster init container
            local initContainer =
                engine.container("pulsar-init")
                    .with_image(images.pulsar)
                    .with_command([
                        "bash",
                        "-c",
                        "sleep 10 && bin/pulsar initialize-cluster-metadata --cluster cluster-a --zookeeper zookeeper:2181 --configuration-store zookeeper:2181 --web-service-url http://pulsar:8080 --broker-service-url pulsar://pulsar:6650",
                    ])
                    .with_limits("1", "512M")
                    .with_reservations("0.05", "512M")
                    .with_environment({
                        "PULSAR_MEM": "-Xms256m -Xmx256m -XX:MaxDirectMemorySize=256m",
                    });


            // Bookkeeper volume
            local bookieVolume = engine.volume("bookie").with_size("20G");

            // Bookkeeper container
            local bookieContainer = 
                engine.container("bookie")
                    .with_image(images.pulsar)
                    .with_command([
                        "bash",
                        "-c",
                        "sleep 5; bin/apply-config-from-env.py conf/bookkeeper.conf && exec bin/pulsar bookie"
                        // false ^ causes this to be a 'failure' exit.
                    ])
                    .with_limits("1", "800M")
                    .with_reservations("0.1", "800M")
                    .with_user(0)
                    .with_volume_mount(bookieVolume, "/pulsar/data/bookkeeper")
                    .with_environment({
                        "clusterName": "cluster-a",
                        "zkServers": "zookeeper:2181",
                        "bookieId": "bookie",
                        "metadataStoreUri": "metadata-store:zk:zookeeper:2181",
                        "advertisedAddress": "bookie",
                        "BOOKIE_MEM": "-Xms512m -Xmx512m -XX:MaxDirectMemorySize=256m",
                    })
                    .with_port(3181, 3181, "bookie");

            // Pulsar broker, stateless (uses ZK and Bookkeeper for state)
            local brokerContainer = 
                engine.container("pulsar")
                    .with_image(images.pulsar)
                    .with_command([
                        "bash",
                        "-c",
                        "bin/apply-config-from-env.py conf/broker.conf && exec bin/pulsar broker"
                    ])
                    .with_limits("1", "800M")
                    .with_reservations("0.1", "800M")
                    .with_environment({
                        "metadataStoreUrl": "zk:zookeeper:2181",
                        "zookeeperServers": "zookeeper:2181",
                        "clusterName": "cluster-a",
                        "managedLedgerDefaultEnsembleSize": "1",
                        "managedLedgerDefaultWriteQuorum": "1",
                        "managedLedgerDefaultAckQuorum": "1",
                        "advertisedAddress": "pulsar",
                        "advertisedListeners": "external:pulsar://pulsar:6650",
                        "PULSAR_MEM": "-Xms512m -Xmx512m -XX:MaxDirectMemorySize=256m",
                    })
                    .with_port(6650, 6650, "pulsar")
                    .with_port(8080, 8080, "admin");

            // Trustgraph Pulsar initialisation
            local adminContainer =
                engine.container("init-trustgraph")
                    .with_image(images.trustgraph)
                    .with_command([
                        "tg-init-pulsar",
                        "-p",
                        url.pulsar_admin,
                    ])
                    .with_limits("1", "128M")
                    .with_reservations("0.1", "128M");

            // Container sets
            local zkContainerSet = engine.containers(
                "zookeeper",
                [
                    zkContainer,
                ]
            );

            local initContainerSet = engine.containers(
                "init-pulsar",
                [
                    initContainer,
                ]
            );

            local bookieContainerSet = engine.containers(
                "bookie",
                [
                    bookieContainer,
                ]
            );

            local brokerContainerSet = engine.containers(
                "broker",
                [
                    brokerContainer,
                ]
            );

            local adminContainerSet = engine.containers(
                "init-pulsar",
                [
                    adminContainer
                ]
            );

            // Zookeeper service
            local zkService =
                engine.service(zkContainerSet)
                .with_port(2181, 2181, "zookeeper")
                .with_port(2888, 2888, "zookeeper2")
                .with_port(3888, 3888, "zookeeper3");

            // Bookkeeper service
            local bookieService =
                engine.service(bookieContainerSet)
                .with_port(3181, 3181, "bookie");

            // Pulsar broker service
            local brokerService =
                engine.service(brokerContainerSet)
                .with_port(6650, 6650, "pulsar")
                .with_port(8080, 8080, "admin");

            engine.resources([
                zkVolume,
                bookieVolume,
                zkContainerSet,
                initContainerSet,
                bookieContainerSet,
                brokerContainerSet,
                adminContainerSet,
                zkService,
                bookieService,
                brokerService,
            ])

    }

}

