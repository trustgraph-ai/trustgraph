// For OpenAI LLMs.  Not currently overriding prompts

local prompts = import "default-prompts.jsonnet";

prompts + {

    // "system-template":: "PROMPT GOES HERE.",

    "templates" +:: {

        "question" +:: {
            // "prompt": "PROMPT GOES HERE",
        },

        "extract-definitions" +:: {
            // "prompt": "PROMPT GOES HERE",
        },

        "extract-relationships" +:: {
            // "prompt": "PROMPT GOES HERE",
        },

        "extract-topics" +:: {
            // "prompt": "PROMPT GOES HERE",
        },

        "extract-rows" +:: {
            // "prompt": "PROMPT GOES HERE",
        },

        "kg-prompt" +:: {
            // "prompt": "PROMPT GOES HERE",
        },

        "document-prompt" +:: {
            // "prompt": "PROMPT GOES HERE",
        },

    }

}

