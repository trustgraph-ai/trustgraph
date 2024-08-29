{
    pattern: {
	name: "prompt-template-rows-template",
        icon: "📜️️💬",
        title: "Specify tablular data / row data extraction prompt",
	description: "Prompt for tableular / row data extraction",
        requires: ["pulsar", "trustgraph"],
        features: ["extract-rows-prompt"],
	args: [
	    {
		name: "prompt",
		type: "string",
		width: 2000,
		description: "Row data extraction prompt",
                default: "<instructions>\nStudy the following text and derive objects which match the schema provided.\n\nYou must output an array of JSON objects for each object you discover\nwhich matches the schema.  For each object, output a JSON object whose fields\ncarry the name field specified in the schema.\n</instructions>\n\n<schema>\n{schema}\n</schema>\n\n<text>\n{text}\n</text>\n\n<requirements>\nYou will respond only with raw JSON format data. Do not provide\nexplanations. Do not add markdown formatting or headers or prefixes.\n</requirements>",
		required: true,
	    }
	]
    },
    module: "prompts/gemini.jsonnet",
}
