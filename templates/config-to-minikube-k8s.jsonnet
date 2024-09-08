
local k8sEngine = import "k8s.jsonnet";
local decode = import "decode-config.jsonnet";
local components = import "components.jsonnet";

// Import config
local config = import "config.json";

// Produce patterns from config
local patterns = decode(config);

local ns = {
    apiVersion: "v1",
    kind: "Namespace",
    metadata: {
        name: "trustgraph",
    },
    "spec": {
    },
};

local engine = k8sEngine + {
    volume:: function(name)
    {
        local volume = self,
        name: name,
        with_size:: function(size) self + { size: size },
        add:: function() [
            {
                apiVersion: "v1",
                kind: "PersistentVolume",
                metadata: {
                    name: volume.name,
                },
                spec: {
                    accessModes: [ "ReadWriteOnce" ],
                    capacity: {
                        storage: volume.size,
                    },
                    persistentVolumeReclaimPolicy: "Delete",
                    hostPath: {
                        path: "/data/pv-" + volume.name,
                    },
                }
            },
            {
                apiVersion: "v1",
                kind: "PersistentVolumeClaim",
                metadata: {
                    name: volume.name,
                    namespace: "trustgraph",
                },
                spec: {
                    accessModes: [ "ReadWriteOnce" ],
                    resources: {
                        requests: {
                            storage: volume.size,
                        }
                    },
                }
            }
        ],

        volRef:: function() {
            name: volume.name,
            persistentVolumeClaim: { claimName: volume.name },
        }

    },

    service:: function(containers)
    {
        local service = self,
        name: containers.name,
        ports: [],
        with_port::
            function(src, dest, name)
                self + {
                    ports: super.ports + [
                        { src: src, dest: dest, name: name  }
                    ]
                },
        add:: function() [
            {
                apiVersion: "v1",
                kind: "Service",
                metadata: {
                    name: service.name,
                    namespace: "trustgraph",
                },
                spec: {
                    selector: {
                        app: service.name,
                    },
                    type: "LoadBalancer",
                    ports: [
                        {
                            port: port.src,
                            targetPort: port.dest,
                            name: port.name,
                        }
                        for port in service.ports
                    ],
                }
            }
        ],
    },

};

//patterns["pulsar"].create(engine)

// Extract resources using the engine
local resources = std.flattenArrays([
    p.create(engine) for p in std.objectValues(patterns)
]);

local resourceList = {
    apiVersion: "v1",
    kind: "List",
    items: [
        ns,
    ] + resources,
};


resourceList

