# tg-invoke-agent

Uses the agent service to answer a question via interactive WebSocket connection.

## Synopsis

```bash
tg-invoke-agent -q "your question" [options]
```

## Description

The `tg-invoke-agent` command provides an interactive interface to TrustGraph's agent service. It connects via WebSocket to submit questions and receive real-time responses, including the agent's thinking process and observations when verbose mode is enabled.

The agent uses available tools and knowledge sources to answer questions, providing a conversational AI interface to your TrustGraph knowledge base.

## Options

### Required Arguments

- `-q, --question QUESTION`: The question to ask the agent

### Optional Arguments

- `-u, --url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `ws://localhost:8088/`)
- `-f, --flow-id FLOW`: Flow ID to use (default: `default`)
- `-U, --user USER`: User identifier (default: `trustgraph`)
- `-C, --collection COLLECTION`: Collection identifier (default: `default`)
- `-l, --plan PLAN`: Agent plan specification (optional)
- `-s, --state STATE`: Agent initial state (optional)
- `-v, --verbose`: Output agent's thinking process and observations

## Examples

### Basic Question
```bash
tg-invoke-agent -q "What is machine learning?"
```

### Verbose Output with Thinking Process
```bash
tg-invoke-agent -q "Explain the benefits of neural networks" -v
```

### Using Specific Flow
```bash
tg-invoke-agent -q "What documents are available?" -f research-flow
```

### With Custom User and Collection
```bash
tg-invoke-agent -q "Show me recent papers" -U alice -C research-papers
```

### Using Custom API URL
```bash
tg-invoke-agent -q "What is AI?" -u ws://production:8088/
```

## Output Format

### Standard Output
The agent provides direct answers to your questions:

```
AI stands for Artificial Intelligence, which refers to computer systems that can perform tasks typically requiring human intelligence.
```

### Verbose Output
With `-v` flag, you see the agent's thinking process:

```
❓ What is machine learning?

🤔 I need to provide a comprehensive explanation of machine learning, including its definition, key concepts, and applications.

💡 Let me search for information about machine learning in the knowledge base.

Machine learning is a subset of artificial intelligence that enables computers to learn and improve automatically from experience without being explicitly programmed...
```

The emoji indicators represent:
- ❓ Your question
- 🤔 Agent's thinking/reasoning
- 💡 Agent's observations from tools/searches

## Error Handling

Common errors and solutions:

### Connection Errors
```bash
Exception: Connection refused
```
**Solution**: Verify the API URL and ensure TrustGraph is running.

### Flow Not Found
```bash
Exception: Invalid flow
```
**Solution**: Check that the specified flow exists and is running using `tg-show-flows`.

### Authentication Errors
```bash
Exception: Unauthorized
```
**Solution**: Verify your authentication credentials and permissions.

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL (converted to WebSocket URL automatically)

## Related Commands

- [`tg-invoke-graph-rag`](tg-invoke-graph-rag.md) - Graph-based retrieval augmented generation
- [`tg-invoke-document-rag`](tg-invoke-document-rag.md) - Document-based retrieval augmented generation
- [`tg-invoke-llm`](tg-invoke-llm.md) - Direct LLM text completion
- [`tg-show-tools`](tg-show-tools.md) - List available agent tools
- [`tg-show-flows`](tg-show-flows.md) - List available flows

## Technical Details

### WebSocket Communication
The command uses WebSocket protocol for real-time communication with the agent service. The URL is automatically converted from HTTP to WebSocket format.

### Message Format
Messages are exchanged in JSON format:

**Request:**
```json
{
    "id": "unique-message-id",
    "service": "agent",
    "flow": "flow-id",
    "request": {
        "question": "your question"
    }
}
```

**Response:**
```json
{
    "id": "unique-message-id",
    "response": {
        "thought": "agent thinking",
        "observation": "agent observation",
        "answer": "final answer"
    },
    "complete": true
}
```

### API Integration
This command uses the [Agent API](../apis/api-agent.md) via WebSocket connection for real-time interaction.

## Use Cases

- **Interactive Q&A**: Ask questions about your knowledge base
- **Research Assistance**: Get help analyzing documents and data
- **Knowledge Discovery**: Explore connections in your data
- **Troubleshooting**: Get help with technical issues using verbose mode
- **Educational**: Learn about topics in your knowledge base