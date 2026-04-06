{

    container:: function(name)
    {

        local container = self,

        name: name,
        limits: {},
        reservations: {},
        ports: [],
        volumes: [],
        bindMounts: [],
        groups: [],
        environment: [],

        with_image:: function(x) self + { image: x },

        with_user:: function(x) self + { user: x },

        with_group:: function(x) self + { groups: super.groups + [x] },

        with_privileged:: function(x) self + { privileged: x },

        with_command:: function(x) self + { command: x },

        with_entrypoint:: function(x) self + { entrypoint: x },

        with_environment:: function(x) self + {
            environment: super.environment + [
                {
                    name: v.key, value: v.value
                }
                for v in std.objectKeysValues(x)
            ],
        },

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

        with_bind_mount::
            function(src, dest)
                local name = "bind-" + std.strReplace(std.strReplace(src, "/", "-"), ".", "-");
                self + {
                    bindMounts: super.bindMounts + [{
                        name: name, src: src, dest: dest
                    }]
                },

        with_port::
            function(src, dest, name) self + {
                ports: super.ports + [
                    { src: src, dest: dest, name : name }
                ]
            },

        with_env_var_secrets::
            function(vars)
                std.foldl(
                    function(obj, x) obj + {
                        environment: super.environment + [{
                            name: x,
                            valueFrom: {
                                secretKeyRef: {
                                    name: vars.name,
                                    key: vars.keyMap[x],
                                }
                            }
                        }]
                    },
                    vars.variables,
                    self
                ),

        add:: function() [

                {
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

                                        // FIXME: Make everything run as
                                        // root.  Needed to get filesystems
                                        // to be accessible.  There's a
                                        // better way of doing this?
                                        securityContext: {
                                            runAsUser: 0,
                                            runAsGroup: 0,
                                        } + (
                                            if std.objectHas(container, "privileged") && container.privileged then
                                            { privileged: true }
                                            else {}
                                        ),

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

                                    (if std.objectHas(container, "entrypoint") then
                                        // Entrypoint is set - use command for entrypoint, args for command
                                        (if std.isString(container.entrypoint) && container.entrypoint == "" then
                                            { command: [] }
                                        else if std.isArray(container.entrypoint) then
                                            { command: container.entrypoint }
                                        else
                                            { command: [container.entrypoint] }
                                        ) + (if std.objectHas(container, "command") then
                                            { args: container.command }
                                        else {})
                                    else if std.objectHas(container, "command") then
                                        { command: container.command }
                                    else {}) +

                                    (if std.length(container.environment) > 0 then
                                    {
                                        env: container.environment,
                                    }
                                    else {}) + 

                (if std.length(container.volumes) > 0 || std.length(container.bindMounts) > 0 then
                {
                    volumeMounts: [
                        {
                            mountPath: vol.mount,
                            name: vol.volume.name,
                        }
                        for vol in container.volumes
                    ] + [
                        {
                            mountPath: bm.dest,
                            name: bm.name,
                        }
                        for bm in container.bindMounts
                    ]
                }

                else
                {}
                )
                            ],
                            volumes: [
                        vol.volume.volRef()
                        for vol in container.volumes
                    ] + [
                        {
                            name: bm.name,
                            hostPath: { path: bm.src }
                        }
                        for bm in container.bindMounts
                            ]
                        } + (
                            if std.length(container.groups) > 0 then
                            { securityContext: { supplementalGroups: container.groups } }
                            else {}
                        )
                    },
                } + {}

                }

            ]

    },

    // Just an alias
    internalService:: self.service,

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

    volume:: function(name)
    {

        local volume = self,

        name: name,

        with_size:: function(size) self + { size: size },

        add:: function() [
                {
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
                    }
                }
            ],

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

        add:: function() [
                {
                    apiVersion: "v1",
                    kind: "ConfigMap",
                    metadata: {
                        name: volume.name,
                        namespace: "trustgraph",
                    },
                    data: parts
                },
            ],


        volRef:: function() {
            name: volume.name,
            configMap: { name: volume.name },
        }

    },

    secretVolume:: function(name, dir, parts)
    {

        local volume = self,

        name: name,

        with_size:: function(size) self + { size: size },

        add:: function() [
        ],

        volRef:: function() {
            name: volume.name,
            secret: { secretName: volume.name },
        }

    },

    envSecrets:: function(name)
    {

        local volume = self,

        name: name,

        variables: [],
        keyMap: {},

        with_size:: function(size) self + { size: size },

        add:: function() [
        ],

        volRef:: function() {
            name: volume.name,
            secret: { secretName: volume.name },
        },

        with_env_var::
            function(name, key) self + {
                variables: super.variables + [name],
                keyMap: super.keyMap + { [name]: key },
            },

    },

    containers:: function(name, containers)
    {

        local cont = self,

        name: name,
        containers: containers,

        add:: function() std.flattenArrays(
            [ c.add() for c in cont.containers ]
        ),

    },

    resources:: function(res)

        std.flattenArrays(
            [ c.add() for c in res ]
        ),

}

