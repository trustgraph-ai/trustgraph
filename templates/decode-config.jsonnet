
local components = import "components.jsonnet";

local apply = function(p, components)

    local component = components[p.name];

    (component + {

        with:: function(k, v) self + {
            [k]:: v
        },

        with_params:: function(pars)
            self + std.foldl(
                function(obj, par) obj.with(par.key, par.value),
                std.objectKeysValues(pars),
                self
            ),

    }).with_params(p.parameters);

local decode = function(config)
    local add = function(state, c) state + apply(c, components);
    local patterns = std.foldl(add, config, {});
    patterns;

decode

