{

    // Extract resources usnig the engine
    package:: function(patterns) {},

    container:: function(name) {

        with_image:: function(x) self + {},

        with_user:: function(x) self + {},

        with_command:: function(x) self + {},

        with_runtime:: function(x) self + {},

        with_privileged:: function(x) self + {},

        with_ipc:: function(x) self + {},

        with_capability:: function(x) self + {},

        with_environment:: function(x) self + {},

        with_device:: function(hdev, cdev) self + {},

        with_limits:: function(c, m) self + {},

        with_reservations:: function(c, m) self + {},

        with_volume_mount:: self + {},

        with_port:: function(src, dest, name) self + {},

        with_env_var_secrets:: function(vars) self + {},

        add:: function() {},
    },

    internalService:: function(containers) {
        with_port:: function(src, dest, name) self + {},
        add:: function() {},
    },

    service:: function(containers) {
        with_port:: function(src, dest, name) self + {},
        add:: function() {},
    },

    volume:: function(name) {
        with_size:: function(size) self + {},
        add:: function() {},
    },

    configVolume:: function(name, dir, parts) {
        add:: function() {},
    },

    secretVolume:: function(name, dir, parts) {
        add:: function() {},
    },

    envSecrets:: function(name) {
        with_env_var:: function(name, key) self + {},
        add:: function() {},
    },

    containers:: function(name, containers) {
        add:: function() {},
    },

    resources:: function(res)
        std.foldl(
            function(state, c) state + c.add(),
            res,
            {}
        ),

}

