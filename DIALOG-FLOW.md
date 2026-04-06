# TrustGraph Configuration Dialog Flow

## Overview

A configuration wizard system that guides users through TrustGraph deployment setup. Outputs deployment configuration and contextual documentation.

Supports two interfaces:
- **Web UI**: Step-by-step wizard with visual cards
- **CLI**: Interactive terminal prompts

## Architecture

```
┌─────────────────────┐
│  trustgraph-flow    │   State machine defining wizard steps
│      .yaml          │   and transitions
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│    Flow Engine      │   Executes state machine, collects user input,
│   (Web UI / CLI)    │   manages state and backtracking
└──────────┬──────────┘
           │
           ▼
    ┌──────────────┐
    │ Wizard State │   Simple key/value object
    │    (JSON)    │   e.g., { platform: "gke", model_deployment: "ollama", ... }
    └──────┬───────┘
           │
     ┌─────┴─────┐
     ▼           ▼
┌─────────┐ ┌─────────────┐
│ Output  │ │Documentation│
│Transform│ │  Assembler  │
└────┬────┘ └──────┬──────┘
     │             │
     ▼             ▼
┌─────────┐ ┌─────────────┐
│Component│ │  README.md  │
│  Array  │ │ / Checklist │
│ (JSON)  │ │   (JSON)    │
└─────────┘ └─────────────┘
```

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Flow structure | State machine | Explicit transitions, supports conditional branching |
| Expression language | JSONata | Single language for conditions and transforms |
| Documentation storage | Manifest + markdown fragments | Clean separation, easy to maintain |
| Platform variants | `in ['docker-compose', 'podman-compose']` | Explicit grouping, no hidden logic |
| Template variables | `{{var}}` syntax | Simple, familiar |

## File Structure

```
config-dialog-flow/
├── dialog-flow-schema.json       # Schema: flow definitions
├── docs-manifest-schema.json     # Schema: documentation manifests
├── trustgraph-flow.yaml          # Flow: wizard state machine
├── trustgraph-output.jsonata     # Transform: state → components
├── trustgraph-docs.yaml          # Manifest: state → documentation
└── docs/                         # Fragments: markdown content
    ├── platform/
    ├── model/
    ├── storage/
    ├── gateway/
    ├── deploy/
    └── features/
```

## Data Flow

1. **Flow engine** loads `trustgraph-flow.yaml`
2. User progresses through steps, engine collects state
3. On completion:
   - **Output transform** evaluates `trustgraph-output.jsonata` against state → component array
   - **Doc assembler** evaluates `trustgraph-docs.yaml` conditions against state → filtered instructions → loads markdown fragments → outputs README or checklist JSON

## Implementation Phases

### Phase 1: Core Flow Engine

- [ ] Parse YAML flow definition
- [ ] Implement state machine executor
- [ ] Handle step rendering (title, description, input)
- [ ] Evaluate JSONata transition conditions
- [ ] Manage wizard state (set values, navigate)
- [ ] Implement backtracking (previous step, state rollback)

### Phase 2: Input Types

- [ ] Select (single choice from options)
- [ ] Toggle (boolean)
- [ ] Number (with min/max/step)
- [ ] Text (free input)
- [ ] Skip single-option steps (UX decision)

### Phase 3: Output Generation

- [ ] Load JSONata transform
- [ ] Evaluate against wizard state
- [ ] Produce component array JSON
- [ ] Package as downloadable ZIP (existing functionality)

### Phase 4: Documentation Assembly

- [ ] Parse documentation manifest
- [ ] Evaluate `when` conditions (JSONata)
- [ ] Filter to matching instructions
- [ ] Load markdown fragments
- [ ] Substitute `{{var}}` placeholders
- [ ] Output as README.md (CLI) or checklist JSON (Web)

### Phase 5: CLI Interface

- [ ] Terminal prompt for each step
- [ ] Numbered option selection
- [ ] Progress indicator (`[3/12]`)
- [ ] Back command
- [ ] Review summary before generate

### Phase 6: Web Interface

- [ ] Step-by-step card UI
- [ ] Progress bar
- [ ] Option cards with icons/descriptions
- [ ] Back navigation
- [ ] Review screen with edit capability
- [ ] Generate button

## Expression Language

All conditions use JSONata:

```
platform = 'docker-compose'
platform in ['gke', 'eks', 'aks', 'minikube']
model_deployment = 'ollama' and platform in ['docker-compose', 'podman-compose']
version < '1.6.0'
ocr.enabled = true
```

## State Shape

```
{
  "version": "1.8.18",
  "platform": "gke",
  "k8s": { "namespace": "trustgraph" },
  "graph_store": "cassandra",
  "vector_db": "qdrant",
  "object_store": "cassandra",
  "model_deployment": "ollama",
  "max_output_tokens": 2048,
  "ocr": { "enabled": true, "engine": "tesseract" },
  "embeddings": { "enabled": false }
}
```

## Out of Scope (Future)

- Dual model mode (separate main/RAG models)
- Advanced settings (concurrency, chunking, memory profiles)
- Configuration import/export
- Validation beyond type checking
