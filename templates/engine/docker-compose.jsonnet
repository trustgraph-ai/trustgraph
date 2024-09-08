{

    // Extract resources usnig the engine
    package:: function(patterns)
        std.foldl(
            function(state, p) state + p.create(self),
            std.objectValues(patterns),
            {}
        ),

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
            services +: {
                [container.name]: {
                    image: container.image,
                    deploy: {
                        resources: {
                            limits: container.limits,
                            reservations: container.reservations,
                        }
                    },
                    restart: "on-failure:100",
                } +

                (if std.objectHas(container, "command") then
                { command: container.command }
                else {}) +

                (if std.objectHas(container, "environment") then
                { environment: container.environment }
                else {}) +

                (if std.length(container.ports) > 0 then
                {
                    ports:  [
                        "%d:%d" % [port.src, port.dest]
                        for port in container.ports
                    ]
                }
                else {}) +

                (if std.length(container.volumes) > 0 then
                {
                    volumes:  [
                        "%s:%s" % [vol.volume.name, vol.mount]
                        for vol in container.volumes
                    ]
                }
                else {})

            }
        }

    },

    internalService:: function(containers)
    {

        local service = self,

        name: containers.name,

        with_port:: function(src, dest, name)
            self + { port: [src, dest] },

        add:: function() {
        }

    },

    service:: function(containers)
    {

        local service = self,

        name: containers.name,

        with_port:: function(src, dest, name)
            self + { port: [src, dest] },

        add:: function() {
        }

    },

    volume:: function(name)
    {

        local volume = self,

        name: name,

        with_size:: function(size) self + { size: size },

        add:: function() {
            volumes +: {
                [volume.name]: {}
            }
        }

    },

    configVolume:: function(name, dir, parts)
    {

        local volume = self,

        name: dir,

        with_size:: function(size) self + { size: size },

        add:: function() {
        }

    },

    secretVolume:: function(name, dir, parts)
    {

        local volume = self,

        name: dir,

        with_size:: function(size) self + { size: size },

        add:: function() {
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

