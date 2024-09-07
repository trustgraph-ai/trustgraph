{

    container:: function(name)
    {

        local container = self,

        name: name,
        limits: {},
        reservations: {},
        ports: [],
        volumes: [],
        securityContext: {
            fsGroup: 1234
//            runAsUser: 65534
//            runAsGroup: 65534
//            runAsNonRoot: true
//            runAsUser: 0,
//            runAsGroup: 0,
//            runAsNonRoot: true,
//            readOnlyRootFilesystem: true,
        },

        with_image:: function(x) self + { image: x },

        with_command:: function(x) self + { command: x },

        with_environment:: function(x) self + { environment: x },

        with_limits:: function(c, m) self + { limits: { cpu: c, memory: m } },

        with_reservations::
            function(c, m) self + { reservations: { cpu: c, memory: m } },

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
                                    { env: [ {
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
                    volumeMounts: [
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
        }

    },

    service:: function(containers)
    {

        local service = self,

        name: containers.name,

        ports: [],

        with_port::
            function(src, dest, name) self + {
                ports: super.ports + [
                    { src: src, dest: dest, name: name }
                ]
            },

        add:: function() {
            resources +: {
                [service.name + "-service"]: {
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
            }
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
                        storageClassName: "tg",
                        capacity: {
                            storage: volume.size,
                        },
                        accessModes: [ "ReadWriteOnce" ],
                        hostPath: {
                            path: "/data/k8s/" + volume.name,
                        }
                    }
                },
                [volume.name + "-pvc"]: {
                    apiVersion: "v1",
                    kind: "PersistentVolumeClaim",
                    metadata: {
                        name: volume.name,
                        namespace: "trustgraph",
                    },
                    spec: {
                        storageClassName: "tg",
                        accessModes: [ "ReadWriteOnce" ],
                        resources: {
                            requests: {
                                storage: volume.size,
                            }
                        },
                        volumeName: volume.name,
                    }
                }
            }
        },

        volRef:: function() {
            name: volume.name,
            persistentVolumeClaim: { claimName: volume.name },
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
                    data: {
                        [item.key]: std.base64(item.value)
                        for item in std.objectKeysValues(parts)
                    }
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

