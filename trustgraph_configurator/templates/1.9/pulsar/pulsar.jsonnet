local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";

// This is a Pulsar configuration.  Non-standalone mode so we deploy
// individual components: bookkeeper, broker and zookeeper.
//
// This also deploys the TrustGraph 'admin' container which initialises
// TrustGraph-specific namespaces etc.

{

    "pulsar" +: {

        // Zookeeper memory settings (can be overridden by memory-profile)
        "zk-memory-limit":: "512M",
        "zk-memory-reservation":: "512M",
        "zk-heap":: "256m",
        "zk-direct-memory":: "256m",

        // Bookie memory settings (can be overridden by memory-profile)
        "bookie-memory-limit":: "1024M",
        "bookie-memory-reservation":: "1024M",
        "bookie-heap":: "256m",
        "bookie-direct-memory":: "256m",

        // Broker memory settings (can be overridden by memory-profile)
        "broker-memory-limit":: "800M",
        "broker-memory-reservation":: "800M",
        "broker-heap":: "384m",
        "broker-direct-memory":: "384m",

        // Pulsar-init memory settings (can be overridden by memory-profile)
        "init-memory-limit":: "256M",
        "init-memory-reservation":: "256M",
        "init-heap":: "128m",
        "init-direct-memory":: "128m",

        create:: function(engine)

            // Capture memory settings into locals (self refers to pulsar object here)
            local zkMemLimit = self["zk-memory-limit"];
            local zkMemReserv = self["zk-memory-reservation"];
            local zkHeap = self["zk-heap"];
            local zkDirect = self["zk-direct-memory"];

            local bookieMemLimit = self["bookie-memory-limit"];
            local bookieMemReserv = self["bookie-memory-reservation"];
            local bookieHeap = self["bookie-heap"];
            local bookieDirect = self["bookie-direct-memory"];

            local brokerMemLimit = self["broker-memory-limit"];
            local brokerMemReserv = self["broker-memory-reservation"];
            local brokerHeap = self["broker-heap"];
            local brokerDirect = self["broker-direct-memory"];

            local initMemLimit = self["init-memory-limit"];
            local initMemReserv = self["init-memory-reservation"];
            local initHeap = self["init-heap"];
            local initDirect = self["init-direct-memory"];

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
                    .with_limits("1", zkMemLimit)
                    .with_reservations("0.05", zkMemReserv)
                    .with_user("0:1000")
                    .with_volume_mount(zkVolume, "/pulsar/data/zookeeper")
                    .with_environment({
                        "metadataStoreUrl": "zk:zookeeper:2181",
                        "PULSAR_MEM": "-Xms%s -Xmx%s -XX:MaxDirectMemorySize=%s" % [
                            zkHeap, zkHeap, zkDirect,
                        ],
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
                    .with_limits("1", initMemLimit)
                    .with_reservations("0.05", initMemReserv)
                    .with_environment({
                        "PULSAR_MEM": "-Xms%s -Xmx%s -XX:MaxDirectMemorySize=%s" % [
                            initHeap, initHeap, initDirect,
                        ],
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
                        "bin/apply-config-from-env.py conf/bookkeeper.conf && exec bin/pulsar bookie"
                        // false ^ causes this to be a 'failure' exit.
                    ])
                    .with_limits("1", bookieMemLimit)
                    .with_reservations("0.1", bookieMemReserv)
                    .with_user("0:1000")
                    .with_volume_mount(bookieVolume, "/pulsar/data/bookkeeper")
                    .with_environment({
                        "clusterName": "cluster-a",
                        "zkServers": "zookeeper:2181",
                        "bookieId": "bookie",
                        "metadataStoreUri": "metadata-store:zk:zookeeper:2181",
                        "advertisedAddress": "bookie",
                        "BOOKIE_MEM": "-Xms%s -Xmx%s -XX:MaxDirectMemorySize=%s" % [
                            bookieHeap, bookieHeap, bookieDirect,
                        ],
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
                    .with_limits("1", brokerMemLimit)
                    .with_reservations("0.1", brokerMemReserv)
                    .with_environment({
                        "metadataStoreUrl": "zk:zookeeper:2181",
                        "zookeeperServers": "zookeeper:2181",
                        "clusterName": "cluster-a",
                        "managedLedgerDefaultEnsembleSize": "1",
                        "managedLedgerDefaultWriteQuorum": "1",
                        "managedLedgerDefaultAckQuorum": "1",
                        "advertisedAddress": "pulsar",
                        "advertisedListeners": "external:pulsar://pulsar:6650,localhost:pulsar://localhost:6650",
                        "PULSAR_MEM": "-Xms%s -Xmx%s -XX:MaxDirectMemorySize=%s" % [
                            brokerHeap, brokerHeap, brokerDirect,
                        ],
                    })
                    .with_port(6650, 6650, "pulsar")
                    .with_port(8080, 8080, "admin");

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
                "pulsar",
                [
                    brokerContainer,
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
                zkService,
                bookieService,
                brokerService,
            ])

    }

}
