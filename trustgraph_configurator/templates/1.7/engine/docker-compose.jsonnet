{

    // Extract resources using the engine
    package:: function(patterns)
        std.foldl(
            function(state, p) state + p.create(self),
            std.objectValues(patterns),
            {}
        ),

    container:: function(name)
    {

        local container = self,

        name:: name,

        with_image:: function(x) self + { image: x },

        with_user:: function(x) self + { user: x },

        with_command:: function(x) self + { command: x },

        with_runtime:: function(x) self + { runtime: x },

        with_privileged:: function(x) self + { privileged: x },

        with_ipc:: function(x) self + { ipc: x },

        with_capability:: function(x) self +
            if std.objectHas(container, "capability") then
              { cap_add: container.capability + x }
            else
              { cap_add: [x], },

        with_environment:: function(x) self +
            if std.objectHas(container, "environment") then
              { environment: container.environment + x }
            else
              { environment: x, },

        with_device:: function(hdev, cdev) self +
            if std.objectHas(container, "devices") then
              { devices: container.devices + "%s:%s" % [hdev, cdev] }
            else
              { devices: [ "%s:%s" % [hdev, cdev] ], },

        with_limits:: function(c, m) self + {
           deploy +: { resources +: {
               limits: { cpus: c, memory: m }
           } },
        },

        with_reservations:: function(c, m) self + {
            deploy +: { resources +: {
                reservations: { cpus: c, memory: m }
            } },
        },

        with_volume_mount::
            function(vol, mnt)
                self + {
                    volumes: 
                        if std.objectHas(container, "volumes") then
                            container.volumes + [
                                "%s:%s" % [vol.volid, mnt]
                            ]
                        else
                            [
                                "%s:%s" % [vol.volid, mnt]
                            ]
                },

        with_port::
            function(src, dest, name)
                self + {
                    ports:
                        if std.objectHas(container, "ports") then
                            container.ports + [ "%d:%d" % [src, dest] ]
                        else
                            [ "%d:%d" % [src, dest] ]
                },

        with_env_var_secrets::
            function(vars)
                std.foldl(
                    function(obj, x) obj.with_environment(
                        { [x]: "${" + x  + "}" }
                    ),
                    vars.variables,
                    self
                ),

        restart: "on-failure:100",

        add:: function() {
            services +: {
                [container.name]: container,
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

        volid:: name,

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

        volid:: "./" + dir,

        with_size:: function(size) self + { size: size },

        add:: function() {
        }

    },

    secretVolume:: function(name, dir, parts)
    {

        local volume = self,

        name: dir,

        volid:: dir,

        with_size:: function(size) self + { size: size },

        add:: function() {
        }

    },

    envSecrets:: function(name)
    {

        local volume = self,

        name: name,

        volid:: name,

        variables:: [],

        with_env_var::
            function(name, key) self + {
                variables: super.variables + [name],
            },

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

