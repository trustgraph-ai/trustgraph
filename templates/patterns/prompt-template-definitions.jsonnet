{
    pattern: {
	name: "prompt-template-definitions",
        icon: "📜️️💬",
        title: "Override definition extraction prompt",
	description: "This pattern overrides the default definition extraction LLM prompt allowing you to provide your own prompt.",
        requires: ["pulsar", "trustgraph"],
        features: ["extract-definition-prompt"],
	args: [
	    {
		name: "prompt-definition-template",
		type: "text",
		width: 2000,
		description: "Definition extraction prompt",
                default: "<instructions>\nStudy the following text and derive definitions for any discovered entities.\nDo not provide definitions for entities whose definitions are incomplete\nor unknown.\nOutput relationships in JSON format as an arary of objects with fields:\n- entity: the name of the entity\n- definition: English text which defines the entity\n</instructions>\n\n<text>\n{text}\n</text>\n\n<requirements>\nYou will respond only with raw JSON format data. Do not provide\nexplanations. Do not use special characters in the abstract text. The\nabstract will be written as plain text.  Do not add markdown formatting\nor headers or prefixes.  Do not include null or unknown definitions.\n</requirements>",
		required: true,
	    }
	],
        category: [ "prompting" ],
    },
    module: "components/null.jsonnet",
}
