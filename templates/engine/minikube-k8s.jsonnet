
local k8s = import "k8s.jsonnet";

local ns = {
    apiVersion: "v1",
    kind: "Namespace",
    metadata: {
        name: "trustgraph",
    },
    "spec": {
    },
};

k8s + {

    // Extract resources usnig the engine
    package:: function(patterns)
        local resources = [ns] + std.flattenArrays([
            p.create(self) for p in std.objectValues(patterns)
        ]);
        local resourceList = {
            apiVersion: "v1",
            kind: "List",
            items: resources,
        };
        resourceList,

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

}

