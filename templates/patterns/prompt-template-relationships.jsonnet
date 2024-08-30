{
    pattern: {
	name: "prompt-template-relationships",
        icon: "📜️️💬",
        title: "Override relationship extraction prompt",
	description: "This pattern overrides the default relationship extraction LLM prompt allowing you to provide your own prompt.",
        requires: ["pulsar", "trustgraph"],
        features: ["extract-relationship-prompt"],
	args: [
	    {
		name: "prompt",
		type: "string",
		width: 2000,
		description: "Relationship extraction prompt",
                default: "<instructions>\nStudy the following text and derive entity relationships.  For each\nrelationship, derive the subject, predicate and object of the relationship.\nOutput relationships in JSON format as an arary of objects with fields:\n- subject: the subject of the relationship\n- predicate: the predicate\n- object: the object of the relationship\n- object-entity: false if the object is a simple data type: name, value or date.  true if it is an entity.\n</instructions>\n\n<text>\n{text}\n</text>\n\n<requirements>\nYou will respond only with raw JSON format data. Do not provide\nexplanations. Do not use special characters in the abstract text. The\nabstract must be written as plain text.  Do not add markdown formatting\nor headers or prefixes.\n</requirements>",
		required: true,
	    }
	]
    },
    module: "components/null.jsonnet",
}
