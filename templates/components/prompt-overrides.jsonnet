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
                        [key] +:: {
                            prompt: value
                        }
                    }
                }
            },

} + default_prompts

