
This is some sketches about how to add an agentic manager with memory.

The existing 'react' manager is going to stay.  The new one will be called
'react_mem'.  The 'react_mem' module is to going to be a drop-in replacement
for 'react' so that the end user can decide which to deploy.

## Interaction start

1. RETRIEVE CONTEXT
   │
   ├── Long-term facts
   │   └── Embed user query → retrieve relevant subgraph
   │
   ├── Episodic memory
   │   └── Embed user query → find similar past episodes
   │
   └── Conversation memory
       └── Pull summary/key points from prior invocations in this conversation
   
2. INITIALIZE WORKING MEMORY
   └── Empty (or seed with "Goal: <user query>")
   
   
## Core loop

┌─────────────────────────────────────────────────────────────────┐
│                         ASSEMBLE CONTEXT                        │
│                                                                 │
│  • System prompt / agent persona                                │
│  • Long-term facts (retrieved at invocation start)              │
│  • Relevant episodes (retrieved at invocation start)            │
│  • Conversation memory (what's happened this conversation)      │
│  • Working memory (steps so far this invocation)                │
│  • Current user query                                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                           REASON                                │
│                                                                 │
│  LLM generates:                                                 │
│  • Thought (reasoning trace)                                    │
│  • Decision: which tool + parameters, OR final answer           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │   Final answer?     │
                    └─────────────────────┘
                         │           │
                        YES          NO
                         │           │
                         ▼           ▼
              ┌──────────────┐  ┌─────────────────────────────────┐
              │   COMPLETE   │  │              ACT                │
              │  (exit loop) │  │                                 │
              └──────────────┘  │  Execute tool, get observation  │
                                └─────────────────────────────────┘
                                                 │
                                                 ▼
                                ┌─────────────────────────────────┐
                                │      UPDATE WORKING MEMORY      │
                                │                                 │
                                │  Append: thought, action, result│
                                │                                 │
                                │  If working memory too large:   │
                                │  → Compress/summarize older     │
                                │    steps, keep recent raw       │
                                └─────────────────────────────────┘
                                                 │
                                                 ▼
                                          (loop back to
                                          ASSEMBLE CONTEXT)
                                          
                                          
## Invocation end

1. EXTRACT & STORE
   │
   ├── Conversation memory
   │   └── Summarize this invocation: "User asked X, agent did Y, result was Z"
   │       Append to conversation memory
   │
   ├── Facts (optional)
   │   └── Did the agent learn anything worth persisting?
   │       If yes → StoreFact (could be automatic extraction or agent-driven)
   │
   └── Episode (if task-like)
       └── RecordEpisode: goal, key steps, outcome, lessons
           Tag with embeddings for future retrieval

2. DISCARD WORKING MEMORY
   └── No longer needed (it's been summarized into conversation memory)
   
   
## Conversation end

1. PROMOTE TO LONG-TERM
   │
   └── Scan conversation memory for facts worth persisting
       → Store to knowledge graph
   
2. RECORD CONVERSATION-LEVEL EPISODE (optional)
   │
   └── If the conversation had an overarching goal/theme,
       capture as a higher-level episode

## Refinements to consider

Refinements to consider:
Mid-invocation retrieval
The initial retrieval might not be enough. Agent could have tools to pull in more:

RetrieveFacts(query) — dig deeper if initial context insufficient
RecallEpisodes(query) — "have I seen this specific problem before?"

Working memory compression trigger

Option A: Every N steps, auto-compress
Option B: When token count exceeds threshold
Option C: Agent explicitly decides ("I should summarize before continuing")

Fact/episode extraction

Option A: Agent explicitly calls StoreFact / RecordEpisode as part of its reasoning
Option B: Post-invocation LLM pass: "Given this invocation, extract any facts/episodes worth storing"
