# tg-invoke-llm

Invokes the text completion service with custom system and user prompts.

## Synopsis

```bash
tg-invoke-llm "system prompt" "user prompt" [options]
```

## Description

The `tg-invoke-llm` command provides direct access to the Large Language Model (LLM) text completion service. It allows you to specify both a system prompt (which sets the AI's behavior and context) and a user prompt (the actual query or task), giving you complete control over the LLM interaction.

This is useful for custom AI tasks, experimentation with prompts, and direct LLM integration without the overhead of retrieval augmented generation or agent frameworks.

## Options

### Required Arguments

- `system`: System prompt that defines the AI's role and behavior
- `prompt`: User prompt containing the actual query or task

### Optional Arguments

- `-u, --url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `http://localhost:8088/`)
- `-f, --flow-id FLOW`: Flow ID to use (default: `default`)

## Arguments

The command requires exactly two positional arguments:

1. **System Prompt**: Sets the AI's context, role, and behavior
2. **User Prompt**: The specific question, task, or content to process

## Examples

### Basic Question Answering
```bash
tg-invoke-llm "You are a helpful assistant." "What is the capital of France?"
```

### Code Generation
```bash
tg-invoke-llm \
  "You are an expert Python programmer." \
  "Write a function to calculate the Fibonacci sequence."
```

### Creative Writing
```bash
tg-invoke-llm \
  "You are a creative writer specializing in science fiction." \
  "Write a short story about time travel in 200 words."
```

### Technical Documentation
```bash
tg-invoke-llm \
  "You are a technical writer who creates clear, concise documentation." \
  "Explain how REST APIs work in simple terms."
```

### Data Analysis
```bash
tg-invoke-llm \
  "You are a data analyst expert at interpreting statistics." \
  "Explain what a p-value means and when it's significant."
```

### Using Specific Flow
```bash
tg-invoke-llm \
  "You are a medical expert." \
  "Explain the difference between Type 1 and Type 2 diabetes." \
  -f medical-flow
```

## System Prompt Design

The system prompt is crucial for getting good results:

### Role Definition
```bash
"You are a [role] with expertise in [domain]."
```

### Behavior Instructions
```bash
"You are helpful, accurate, and concise. Always provide examples."
```

### Output Format
```bash
"You are a technical writer. Always structure your responses with clear headings and bullet points."
```

### Constraints
```bash
"You are a helpful assistant. Keep responses under 100 words and always cite sources when possible."
```

## Output Format

The command returns the LLM's response directly:

```
The capital of France is Paris. Paris has been the capital city of France since the late 10th century and is located in the north-central part of the country along the Seine River. It is the most populous city in France with over 2 million inhabitants in the city proper and over 12 million in the metropolitan area.
```

## Prompt Engineering Tips

### Effective System Prompts
- **Be Specific**: Clearly define the AI's role and expertise
- **Set Tone**: Specify the desired communication style
- **Include Constraints**: Set limits on response length or format
- **Provide Context**: Give relevant background information

### Effective User Prompts
- **Be Clear**: State exactly what you want
- **Provide Examples**: Show the desired output format
- **Add Context**: Include relevant background information
- **Specify Format**: Request specific output structure

## Error Handling

### Flow Not Available
```bash
Exception: Invalid flow
```
**Solution**: Verify the flow exists and is running with `tg-show-flows`.

### Connection Errors
```bash
Exception: Connection refused
```
**Solution**: Check the API URL and ensure TrustGraph is running.

### Prompt Errors
```bash
Exception: Invalid prompt format
```
**Solution**: Ensure both system and user prompts are provided as separate arguments.

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL

## Related Commands

- [`tg-invoke-agent`](tg-invoke-agent.md) - Interactive agent with tools and reasoning
- [`tg-invoke-graph-rag`](tg-invoke-graph-rag.md) - Graph-based retrieval augmented generation
- [`tg-invoke-document-rag`](tg-invoke-document-rag.md) - Document-based retrieval augmented generation
- [`tg-invoke-prompt`](tg-invoke-prompt.md) - Use predefined prompt templates

## API Integration

This command uses the [Text Completion API](../apis/api-text-completion.md) to perform direct LLM inference with custom prompts.

## Use Cases

### Development and Testing
```bash
# Test prompt variations
tg-invoke-llm "You are a code reviewer." "Review this Python function: def add(a, b): return a + b"

# Experiment with different system prompts
tg-invoke-llm "You are a harsh critic." "What do you think of Python?"
tg-invoke-llm "You are an enthusiastic supporter." "What do you think of Python?"
```

### Content Generation
```bash
# Blog post writing
tg-invoke-llm \
  "You are a technical blogger who writes engaging, informative content." \
  "Write an introduction to machine learning for beginners."

# Marketing copy
tg-invoke-llm \
  "You are a marketing copywriter focused on clear, compelling messaging." \
  "Write a product description for a cloud storage service."
```

### Educational Applications
```bash
# Concept explanation
tg-invoke-llm \
  "You are a teacher who explains complex topics in simple terms." \
  "Explain quantum computing to a high school student."

# Study guides
tg-invoke-llm \
  "You are an educational content creator specializing in study materials." \
  "Create a study guide for photosynthesis."
```

### Business Applications
```bash
# Report summarization
tg-invoke-llm \
  "You are a business analyst who creates executive summaries." \
  "Summarize the key points from this quarterly report: [report text]"

# Email drafting
tg-invoke-llm \
  "You are a professional communication expert." \
  "Draft a polite follow-up email for a job interview."
```

### Research and Analysis
```bash
# Literature review
tg-invoke-llm \
  "You are a research academic who analyzes scientific literature." \
  "What are the current trends in renewable energy research?"

# Competitive analysis
tg-invoke-llm \
  "You are a market research analyst." \
  "Compare the features of different cloud computing platforms."
```

## Advanced Techniques

### Multi-step Reasoning
```bash
# Chain of thought prompting
tg-invoke-llm \
  "You are a logical reasoner. Work through problems step by step." \
  "If a train travels 60 mph for 2 hours, then 80 mph for 1 hour, what's the average speed?"
```

### Format Control
```bash
# JSON output
tg-invoke-llm \
  "You are a data processor. Always respond with valid JSON." \
  "Convert this to JSON: Name: John, Age: 30, City: New York"

# Structured responses
tg-invoke-llm \
  "You are a technical writer. Use markdown formatting with headers and lists." \
  "Explain the software development lifecycle."
```

### Domain Expertise
```bash
# Legal analysis
tg-invoke-llm \
  "You are a legal expert specializing in contract law." \
  "What are the key elements of a valid contract?"

# Medical information
tg-invoke-llm \
  "You are a medical professional. Provide accurate, evidence-based information." \
  "What are the symptoms of Type 2 diabetes?"
```

## Best Practices

1. **Clear System Prompts**: Define the AI's role and behavior explicitly
2. **Specific User Prompts**: Be precise about what you want
3. **Iterative Refinement**: Experiment with different prompt variations
4. **Output Validation**: Verify the quality and accuracy of responses
5. **Appropriate Flows**: Use flows configured for your specific domain
6. **Length Considerations**: Balance detail with conciseness in prompts