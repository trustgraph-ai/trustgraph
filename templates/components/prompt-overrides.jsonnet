local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";
local default_prompts = import "prompts/default-prompts.jsonnet";

{

    with:: function(key, value)
        if (key == "system-template") then
            self + {
                prompts +:: {
                    "system-template": value,
                }
            }
        else
            self + {
                prompts +:: {
                    templates +:: {
                        [key]: {
                            prompt +:: value
                        }
                    }
                }
            },

} + default_prompts

