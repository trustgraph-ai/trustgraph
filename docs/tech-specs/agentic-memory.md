# Agentic Memory Technical Specification

## Overview

This specification describes the implementation of an agent manager with multi-layered memory capabilities for TrustGraph. The new `react_mem` module extends the existing ReAct pattern with persistent memory across invocations and conversations, enabling agents to learn from past interactions and maintain context over time.

The implementation supports the following use cases:

1. **Long-term Knowledge Retention**: Store and retrieve factual information learned during agent interactions
2. **Episodic Memory**: Remember past problem-solving approaches and their outcomes
3. **Conversation Continuity**: Maintain context across multiple invocations within a conversation
4. **Working Memory Management**: Handle extended reasoning chains with automatic compression
5. **Experience-Based Reasoning**: Leverage similar past experiences when addressing new queries

## Goals

- **Drop-in Compatibility**: `react_mem` implements the same AgentService interface as `react`, allowing users to choose between implementations via configuration
- **Memory Persistence**: Enable agents to retain and retrieve information across invocations and conversations
- **Scalable Context Management**: Handle long-running conversations without unbounded memory growth
- **Retrieval Efficiency**: Use embedding-based retrieval to surface relevant memory efficiently
- **Incremental Adoption**: Deploy alongside existing `react` module without breaking changes
- **Transparent Operation**: Memory operations should not significantly impact response latency
- **Configurable Behavior**: Allow tuning of memory extraction, compression, and retrieval strategies

## Background

### Current Architecture

The existing `react` agent manager (module: `trustgraph-flow/trustgraph/agent/react/`) implements a stateless ReAct (Reasoning and Acting) loop:

1. Receives `AgentRequest` with question and history
2. Reasons about the problem using LLM
3. Takes action by invoking tools
4. Returns `AgentResponse` with thought, observation, or final answer
5. Maintains working memory only for the current invocation via `history` field

Current limitations include:

- **No Long-term Memory**: Each invocation starts fresh with no access to prior conversations
- **Limited Context Window**: History is bounded by max iterations and token limits
- **No Learning**: Agent cannot benefit from past problem-solving experiences
- **Conversation Fragmentation**: No mechanism to connect related invocations across a conversation
- **Context Loss**: Important information from early steps may be lost as history grows

This specification addresses these gaps by introducing a four-tier memory architecture. By maintaining long-term facts, episodic memories, conversation summaries, and managed working memory, TrustGraph agents can:

- Build and leverage a persistent knowledge base
- Learn from past successes and failures
- Maintain coherent context across extended conversations
- Handle complex multi-step reasoning without context overflow

## Technical Design

### Architecture

The agentic memory system requires the following technical components:

1. **ReactMemAgentManager**
   - Extends AgentManager with memory-aware reasoning loop
   - Orchestrates memory retrieval at invocation start
   - Manages working memory compression during execution
   - Triggers memory extraction at invocation end

   Module: `trustgraph-flow/trustgraph/agent/react_mem/agent_manager.py`

2. **ReactMemService**
   - Implements AgentService interface (drop-in replacement for react.Processor)
   - Manages conversation-level memory lifecycle
   - Handles configuration of memory services and policies
   - Coordinates memory promotion at conversation end

   Module: `trustgraph-flow/trustgraph/agent/react_mem/service.py`

3. **Memory Services** (Implementation Details: TBD)
   - Long-term Facts Service
   - Episodic Memory Service
   - Conversation Memory Service
   - Working Memory Management Service

   Module: `trustgraph-flow/trustgraph/agent/react_mem/memory/` (TBD)

4. **Memory Schema Definitions**
   - Data structures for facts, episodes, conversation records
   - Request/response schemas for memory operations

   Module: `trustgraph-base/trustgraph/schema/agent_memory.py`

### Memory Architecture

#### Four-Tier Memory System

**Long-term Facts**
- **Purpose**: Persistent knowledge graph of facts learned across all conversations
- **Scope**: Global per user/collection
- **Retrieval**: Embedding-based semantic search on user query
- **Lifetime**: Permanent until explicitly deleted
- **Storage**: Graph database (existing TrustGraph knowledge store)

**Episodic Memory**
- **Purpose**: Records of past problem-solving episodes with outcomes
- **Scope**: Global per user/collection
- **Retrieval**: Embedding-based similarity search on current goal/context
- **Lifetime**: Permanent with optional TTL or relevance-based pruning
- **Storage**: Vector store with structured metadata

**Conversation Memory**
- **Purpose**: Summaries and key points from prior invocations in current conversation
- **Scope**: Current conversation only
- **Retrieval**: Sequential access (not searched)
- **Lifetime**: Duration of conversation
- **Storage**: In-memory with optional persistence for long conversations

**Working Memory**
- **Purpose**: Reasoning trace for current invocation (thoughts, actions, observations)
- **Scope**: Current invocation only
- **Retrieval**: Directly included in LLM context
- **Lifetime**: Current invocation (discarded after summarization)
- **Storage**: In-memory list

### Data Models

#### Memory Records

**Fact Record**
```
Fact:
  - id: string (unique identifier)
  - content: string (fact statement)
  - source: string (conversation_id where learned)
  - timestamp: datetime
  - embedding: vector
  - metadata: dict
```

**Episode Record**
```
Episode:
  - id: string (unique identifier)
  - goal: string (what was being attempted)
  - steps: list[string] (key actions taken)
  - outcome: string (result achieved)
  - lessons: string (insights/learnings)
  - timestamp: datetime
  - embedding: vector
  - metadata: dict
```

**Conversation Record**
```
ConversationMemory:
  - conversation_id: string
  - invocations: list[InvocationSummary]
  - metadata: dict

InvocationSummary:
  - query: string
  - summary: string (what agent did)
  - result: string (outcome)
  - timestamp: datetime
```

**Working Memory Item**
```
WorkingMemoryItem:
  - type: enum[thought, action, observation]
  - content: string
  - timestamp: datetime
  - metadata: dict (e.g., token_count)
```

### Memory Operations Lifecycle

#### Invocation Start: Context Assembly

When `ReactMemService` receives an `AgentRequest`:

1. **Retrieve Long-term Facts**
   - Embed user query
   - Query facts store with embedding
   - Retrieve top-k relevant facts (configurable k)

2. **Retrieve Episodic Memory**
   - Embed user query + current state
   - Query episodes store with embedding
   - Retrieve top-k similar past episodes

3. **Load Conversation Memory**
   - Fetch conversation record by conversation_id
   - Load all prior invocation summaries for this conversation

4. **Initialize Working Memory**
   - Create empty working memory buffer
   - Optionally seed with high-level goal

These retrieved memories are assembled into the context passed to `ReactMemAgentManager.reason()`.

#### Core Loop: Memory-Aware Reasoning

The reasoning loop proceeds similarly to standard ReAct, but with augmented context:

1. **Assemble Context**
   - System prompt / agent persona
   - Long-term facts (from retrieval)
   - Relevant episodes (from retrieval)
   - Conversation memory (loaded summaries)
   - Working memory (current invocation trace)
   - Current user query

2. **Reason**
   - LLM generates thought and decision
   - Returns Action (tool call) or Final (answer)

3. **Act** (if Action)
   - Execute tool
   - Get observation result

4. **Update Working Memory**
   - Append thought, action, observation to working memory
   - Check working memory size
   - If exceeds threshold: compress older entries, preserve recent ones

5. **Loop** until Final answer or max iterations

**Working Memory Compression Trigger**: When token count of working memory exceeds threshold (e.g., 50% of context window), invoke summarization:
- Keep most recent N steps verbatim
- Summarize older steps into condensed form
- Preserve critical information (tool results, key decisions)

#### Invocation End: Memory Extraction

After sending final response:

1. **Conversation Memory Update**
   - Generate invocation summary: "User asked X, agent did Y, result was Z"
   - Append summary to conversation memory

2. **Fact Extraction** (Optional/Conditional)
   - LLM pass: "Did the agent learn anything worth persisting?"
   - If yes: Extract fact statements, store to long-term facts
   - Alternative: Agent explicitly calls StoreFact tool during reasoning

3. **Episode Recording** (If Task-Like)
   - If invocation resembled a task (multi-step problem solving):
     - Extract: goal, key steps, outcome, lessons learned
     - Generate embedding for retrieval
     - Store to episodic memory

4. **Discard Working Memory**
   - Working memory cleared (already summarized)

#### Conversation End: Memory Promotion

When conversation concludes (explicit signal or timeout):

1. **Promote Facts to Long-term**
   - Scan conversation memory for high-value facts
   - Store to persistent knowledge graph
   - Update graph embeddings for retrieval

2. **Record Conversation Episode** (Optional)
   - If conversation had overarching theme/goal:
     - Summarize entire conversation as high-level episode
     - Store to episodic memory

### APIs

#### New Memory Service APIs

**Fact Retrieval**
```
RetrieveFactsRequest:
  - query: string (search query)
  - embedding: vector (pre-computed)
  - top_k: int (default: 5)
  - user: string
  - collection: string

RetrieveFactsResponse:
  - facts: list[Fact]
  - error: Error
```

**Episode Retrieval**
```
RetrieveEpisodesRequest:
  - query: string
  - embedding: vector
  - top_k: int (default: 3)
  - user: string
  - collection: string

RetrieveEpisodesResponse:
  - episodes: list[Episode]
  - error: Error
```

**Fact Storage**
```
StoreFactRequest:
  - content: string
  - source: string (conversation_id)
  - user: string
  - collection: string
  - metadata: dict

StoreFactResponse:
  - fact_id: string
  - error: Error
```

**Episode Storage**
```
StoreEpisodeRequest:
  - goal: string
  - steps: list[string]
  - outcome: string
  - lessons: string
  - user: string
  - collection: string
  - metadata: dict

StoreEpisodeResponse:
  - episode_id: string
  - error: Error
```

**Conversation Memory Management**
```
GetConversationMemoryRequest:
  - conversation_id: string
  - user: string

GetConversationMemoryResponse:
  - conversation: ConversationMemory
  - error: Error

UpdateConversationMemoryRequest:
  - conversation_id: string
  - invocation_summary: InvocationSummary
  - user: string

UpdateConversationMemoryResponse:
  - success: boolean
  - error: Error
```

#### Modified Agent APIs

**AgentRequest** (Extended)
```
AgentRequest:
  # Existing fields
  - question: string
  - history: list[AgentStep]
  - user: string
  - streaming: boolean
  - state: string
  - group: list[string]

  # New fields for memory
  - conversation_id: string (identifies conversation for memory retrieval)
  - enable_memory: boolean (default: false, set true for react_mem)
```

**AgentResponse** (No changes required)
- Existing schema supports memory-enabled agents
- Memory operations are transparent to client

### Implementation Details

#### Service Configuration

The `react_mem` service will be configured similarly to `react`, with additional memory-related parameters:

Configuration key: `agent-mem` (distinct from `agent` used by react)

Configuration parameters:
- `max-iterations`: Maximum ReAct loop iterations
- `working-memory-threshold`: Token count trigger for compression (default: 2000)
- `fact-retrieval-top-k`: Number of facts to retrieve (default: 5)
- `episode-retrieval-top-k`: Number of episodes to retrieve (default: 3)
- `enable-auto-fact-extraction`: Auto-extract facts at invocation end (default: true)
- `enable-episode-recording`: Auto-record episodes (default: true)
- `additional-context`: Additional system context (same as react)

#### Memory Service Specifications

**Memory service implementation details are TBD and will be defined in a separate technical specification.**

The memory services must implement the following interfaces:

1. **Long-term Facts Service**
   - Interface: Fact storage, retrieval, deletion
   - Storage backend: TBD (likely existing graph store + vector index)
   - Embedding model: TBD (consistency with existing embeddings)

2. **Episodic Memory Service**
   - Interface: Episode storage, retrieval, search
   - Storage backend: TBD (vector store + structured metadata store)
   - Retention policy: TBD

3. **Conversation Memory Service**
   - Interface: CRUD operations on conversation records
   - Storage backend: TBD (in-memory with optional persistence)
   - TTL/cleanup policy: TBD

4. **Working Memory Manager**
   - Interface: Append, compress, retrieve working memory
   - Compression strategy: TBD (summarization vs. truncation)
   - Implementation: In-memory only

These services will be registered as client specifications similar to existing services (GraphRagClientSpec, ToolClientSpec, etc.).

#### Prompt Engineering

The memory-aware prompts will need to incorporate retrieved context effectively:

**Prompt structure** (conceptual):
```
System: You are an agent with access to persistent memory...

Long-term Facts:
- [Retrieved fact 1]
- [Retrieved fact 2]
...

Relevant Past Episodes:
- Episode 1: [summary]
- Episode 2: [summary]
...

Conversation History:
- Previous invocation 1: [summary]
- Previous invocation 2: [summary]
...

Current Task:
Working Memory:
- [Current steps taken]

Question: [User query]

Think step by step and decide on next action or provide final answer.
```

Prompt templates will be defined in configuration, similar to existing agent prompts.

#### Tool Extensions (Optional Refinement)

To support mid-invocation retrieval (optional future enhancement):

**RetrieveFacts Tool**
- Description: "Retrieve additional facts from knowledge base"
- Arguments: query (string)
- Implementation: Calls fact retrieval service

**RecallEpisodes Tool**
- Description: "Search for similar past problem-solving episodes"
- Arguments: query (string)
- Implementation: Calls episode retrieval service

**StoreFact Tool**
- Description: "Explicitly store a fact for future reference"
- Arguments: fact_content (string)
- Implementation: Calls fact storage service

These tools would be optional and configured per deployment.

### Client Specifications

The react_mem service will register the following client specifications:

**Existing (inherited from react):**
- TextCompletionClientSpec
- GraphRagClientSpec
- PromptClientSpec
- ToolClientSpec
- StructuredQueryClientSpec

**New (memory-specific):**
- FactRetrievalClientSpec
- EpisodeRetrievalClientSpec
- FactStorageClientSpec
- EpisodeStorageClientSpec
- ConversationMemoryClientSpec

## Security Considerations

**Memory Isolation**
- All memory operations must be scoped to user and collection
- Cross-user memory leakage must be prevented
- Fact and episode retrieval must respect access controls

**PII and Sensitive Information**
- Fact extraction should avoid storing sensitive personal information
- Conversation memory may contain PII and must be handled accordingly
- Memory retention policies should align with privacy requirements
- Option to disable memory or purge memory for specific users/conversations

**Embedding Security**
- Embeddings may leak information through similarity searches
- Consider privacy-preserving embedding techniques for sensitive deployments

**Resource Limits**
- Prevent unbounded memory growth through:
  - Per-user/collection memory quotas
  - Time-based expiration of old memories
  - Relevance-based pruning of unused memories

## Performance Considerations

**Retrieval Latency**
- Embedding generation adds latency at invocation start
- Vector searches for facts and episodes may add 50-200ms per retrieval
- Mitigation: Parallel retrieval of facts and episodes, caching embeddings

**Context Window Usage**
- Retrieved memories consume context window
- Must balance memory breadth vs. depth
- Working memory compression necessary to avoid overflow

**Storage Overhead**
- Each conversation generates conversation memory records
- Each invocation may create fact and episode records
- Mitigation: Background cleanup jobs, retention policies

**Scaling**
- Memory stores must scale with user base
- Vector search performance critical for large fact/episode databases
- Consider sharding strategies for multi-tenant deployments

## Testing Strategy

**Unit Tests**
- Memory service interfaces (mocked backends)
- Working memory compression logic
- Prompt assembly with memory context
- Fact/episode extraction logic

**Integration Tests**
- End-to-end agent invocation with memory enabled
- Memory retrieval and storage flows
- Conversation continuity across invocations
- Working memory compression triggers

**Performance Tests**
- Latency impact of memory retrieval
- Context window utilization with varying memory sizes
- Large-scale memory retrieval (1000s of facts/episodes)

**Correctness Tests**
- Verify facts are correctly stored and retrieved
- Verify episodes improve problem-solving on similar tasks
- Verify conversation memory maintains coherence

## Migration Plan

**Phase 1: Module Creation**
- Create `react_mem` directory structure
- Implement ReactMemService and ReactMemAgentManager shells
- No memory operations yet (functionally equivalent to react)
- Deploy and verify drop-in compatibility

**Phase 2: Memory Services**
- Implement memory service interfaces and backends
- Add memory retrieval at invocation start (read-only)
- Deploy and verify retrieval performance

**Phase 3: Memory Writing**
- Enable conversation memory updates
- Enable fact and episode extraction
- Deploy with memory writing enabled

**Phase 4: Conversation Lifecycle**
- Implement conversation-end memory promotion
- Add cleanup and retention policies
- Full agentic memory capabilities enabled

**Rollout Strategy**
- Deploy react_mem alongside react (not as replacement)
- Users opt-in by changing configuration to use react_mem
- Monitor performance and memory growth
- Gradually migrate users based on feedback

## Timeline

- **Phase 1 (Module Creation)**: 1-2 weeks
- **Phase 2 (Memory Services)**: 3-4 weeks (dependent on memory service spec)
- **Phase 3 (Memory Writing)**: 2-3 weeks
- **Phase 4 (Conversation Lifecycle)**: 1-2 weeks
- **Total**: 7-11 weeks

## Open Questions

- **Embedding Model**: Should we use the same embedding model as existing graph RAG, or introduce a dedicated memory embedding model?
- **Fact Extraction Trigger**: Auto-extract via LLM pass, or require explicit StoreFact tool usage?
- **Conversation End Detection**: How do we reliably detect conversation end (timeout, explicit signal, heuristic)?
- **Memory Cleanup**: What retention policies for facts, episodes, and conversation memory?
- **Cross-conversation Learning**: Should episodic memory span conversations, or be scoped per conversation?
- **Working Memory Compression**: Summarization (LLM-based) or truncation (rule-based)?
- **Memory Search UX**: Should memory retrieval be visible to users, or completely transparent?
- **Backward Compatibility**: Should react service gain `conversation_id` field for potential future memory support?

## References

- Existing react agent implementation: `trustgraph-flow/trustgraph/agent/react/`
- AgentService base class: `trustgraph-base/trustgraph/base/agent_service.py`
- Agent schemas: `trustgraph-base/trustgraph/schema/services/agent.py`
- Similar memory-augmented agent architectures: Reflexion, MemGPT, ChatGPT memory features
