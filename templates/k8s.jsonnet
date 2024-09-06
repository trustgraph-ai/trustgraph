{

    container:: function(name)
    {

        local container = self,

        name: name,
        limits: {},
        reservations: {},
        ports: [],
        volumes: [],

        with_image:: function(x) self + { image: x },

        with_command:: function(x) self + { command: x },

        with_environment:: function(x) self + { environment: x },

        with_limits:: function(c, m) self + { limits: { cpus: c, memory: m } },

        with_reservations::
            function(c, m) self + { reservations: { cpus: c, memory: m } },

        with_volume_mount::
            function(vol, mnt)
                self + {
                    volumes: super.volumes + [{
                        volume: vol, mount: mnt
                    }]
                },

        with_port::
            function(src, dest, name) self + {
                ports: super.ports + [
                    { src: src, dest: dest, name : name }
                ]
            },

        add:: function() {

            resources +: {
                [container.name]: {
                    apiVersion: "apps/v1",
                    kind: "Deployment",
                    metadata: {
                        name: container.name,
                        namespace: "trustgraph",
                        labels: {
                            app: container.name
                        }
                    },
                    spec: {
                        replicas: 1,
                        selector: {
                            matchLabels: {
                                app: container.name,
                            }
                        }
                    },
                    template: {
                        metadata: {
                            labels: {
                                app: container.name,
                            }
                        },
                        spec: {
                            containers: [
                                {
                                    name: container.name,
                                    image: container.image,
                                    resources: {
                                        requests: container.reservations,
                                        limits: container.limits
                                    },
                                } + (
                                if std.length(container.ports) > 0 then
                                {
                                    ports:  [
                                        {
                                            hostPort: port.src,
                                            containerPort: port.dest,
                                        }
                                        for port in container.ports
                                    ]
                                } else
                                {}) + 

                                (if std.objectHas(container, "command") then
                                { command: container.command }
                                else {}) + 
                                (if std.objectHas(container, "environment") then
                                { environment: [ {
                                    name: e.key, value: e.value
                                    }
                                    for e in 
                                    std.objectKeysValues(
                                        container.environment
                                        )
                                        ]
                                        }
                                else {}) + 

                (if std.length(container.volumes) > 0 then
                {
                    volumes: [
                        {
                            mountPath: vol.mount,
                            name: vol.volume.name,
                        }
                        for vol in container.volumes
                    ]
                }

                else
                {}
                )
                            ],
                            volumes: [
                        vol.volume.volRef()
                        for vol in container.volumes

                            ]
                        }
                    },
                } + {} 

            }
        }

    },

    service:: function(containers)
    {

        local service = self,

        name: containers.name,

        with_port:: function(src, dest) self + { port: [src, dest] },

        add:: function() {
        }

    },

    volume:: function(name)
    {

        local volume = self,

        name: name,

        with_size:: function(size) self + { size: size },

        add:: function() {
            resources +: {
                [volume.name + "-pv"]: {
                    apiVersion: "v1",
                    kind: "PersistentVolume",
                    metadata: {
                        name: volume.name,
                        labels: {
                            type: "local",
                        }
                    },
                    spec: {
                        storageClassName: "manual",
                        capacity: {
                            storage: volume.size,
                        },
                        accessModes: [ "ReadWriteOnce" ],
                        hostPath: {
                            path: "/mnt/" + volume.name,
                        }
                    }
                },
                [volume.name + "-pvc"]: {
                    apiVersion: "v1",
                    kind: "PersistentVolumeClaim",
                    metadata: {
                        name: volume.name,
                    },
                    spec: {
                        storageClassName: "manual",
                        accessModes: [ "ReadWriteOnce" ],
                        resources: {
                            requests: {
                                storage: volume.size,
                            }
                        },
                        volumeName: volume.name + "-pv",
                    }
                }
            }
        },

        volRef:: function() {
            name: volume.name,
            persistentVolumeClaim: { name: volume.name + "-pvc" },
        }

    },

    configVolume:: function(name, dir, parts)
    {

        local volume = self,

        name: name,

        with_size:: function(size) self + { size: size },

        add:: function() {
            resources +: {
                [volume.name + "-cm"]: {
                    apiVersion: "v1",
                    kind: "ConfigMap",
                    metadata: {
                        name: volume.name,
                        namespace: "trustgraph",
                    },
                    data: parts
                },
            }
        },

        volRef:: function() {
            name: volume.name,
            configMap: { name: volume.name + "-cm" },
        }

    },

    secretVolume:: function(name, dir, parts)
    {

        local volume = self,

        name: name,

        with_size:: function(size) self + { size: size },

        add:: function() {
            resources +: {
                [volume.name + "-cm"]: {
                    apiVersion: "v1",
                    kind: "Secret",
                    metadata: {
                        name: volume.name,
                        namespace: "trustgraph",
                    },
                    data: parts
                },
            }
        },

        volRef:: function() {
            name: volume.name,
            secret: { secretName: volume.name + "-cm" },
        }

    },

    containers:: function(name, containers)
    {

        local cont = self,

        name: name,
        containers: containers,

        add:: function() std.foldl(
            function(state, c) state + c.add(),
            cont.containers,
            {}
        ),

    },

    resources:: function(res)
        std.foldl(
            function(state, c) state + c.add(),
            res,
            {}
        ),

}

