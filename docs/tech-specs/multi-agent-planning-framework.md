# TechSpec: Multi-Agent Planning Framework (MAPF)

## Overview

The Multi-Agent Planning Framework (MAPF) is a confidence-driven agent architecture that complements the existing ReAct framework. While ReAct uses iterative reasoning cycles, MAPF generates upfront execution plans with confidence thresholds and executes them through specialized microservices.

## Architecture Design

### Core Philosophy
- **Confidence-Driven Execution**: Each step has confidence thresholds that determine progression
- **Upfront Planning**: Generate complete execution plans before execution begins
- **Specialized Functions**: Domain-specific microservices for different operation types
- **Fault Tolerance**: Retry mechanisms and fallback strategies based on confidence scores

### System Components

#### 1. Planning Service (`trustgraph-mapf-planning`)

**Responsibility**: Generate execution plans from user requests

**Input Schema**:
```python
@dataclasses.dataclass
class PlanRequest:
    user_request: str
    context: Optional[dict] = None
    constraints: Optional[dict] = None
```

**Output Schema**:
```python
@dataclasses.dataclass
class ExecutionPlan:
    plan_id: str
    steps: List[PlanStep]
    confidence_threshold: float = 0.7
    max_retries: int = 3
    
@dataclasses.dataclass
class PlanStep:
    step_id: str
    function_type: str  # query, external_query, compare, evaluate, etc.
    parameters: dict
    confidence_threshold: float
    dependencies: List[str]  # Previous step IDs this depends on
    retry_strategy: Optional[dict] = None
```

**Implementation**:
- Uses LLM to decompose complex requests into structured plans
- Assigns confidence thresholds based on task complexity
- Determines step dependencies and execution order

#### 2. Flow Controller Service (`trustgraph-mapf-controller`)

**Responsibility**: Orchestrate plan execution across microservices

**Key Features**:
- Step dependency resolution
- Confidence score validation
- Retry logic and failure handling
- Context management between steps

**Execution Logic**:
```python
async def execute_plan(self, plan: ExecutionPlan):
    context = ExecutionContext(plan_id=plan.plan_id)
    
    for step in plan.steps:
        if not self.dependencies_satisfied(step, context):
            await self.wait_for_dependencies(step, context)
        
        result = await self.execute_step(step, context)
        
        if result.confidence < step.confidence_threshold:
            if context.retries[step.step_id] < plan.max_retries:
                await self.retry_step(step, context)
            else:
                await self.handle_failure(step, context)
        else:
            context.add_result(step.step_id, result)
```

#### 3. Function Services

Specialized microservices for different operation types:

##### Query Service (`trustgraph-mapf-query`)
- Internal knowledge base queries
- Uses existing graph RAG infrastructure
- Handles collection-specific queries

##### External Query Service (`trustgraph-mapf-external`)
- Web searches, API calls
- Rate limiting and error handling
- Response validation and confidence scoring

##### Processing Services:
- **Compare Service** (`trustgraph-mapf-compare`): Data comparison operations
- **Evaluate Service** (`trustgraph-mapf-evaluate`): Assessment and scoring
- **Compute Service** (`trustgraph-mapf-compute`): Mathematical operations
- **Filter Service** (`trustgraph-mapf-filter`): Data filtering and selection
- **Prioritize Service** (`trustgraph-mapf-prioritize`): Ranking and ordering
- **Deduce Service** (`trustgraph-mapf-deduce`): Logical inference

##### Document Service (`trustgraph-mapf-document`)
- Final output generation
- Report compilation
- Format conversion

#### 4. Data Store Service (`trustgraph-mapf-datastore`)

**Responsibility**: Execution context and intermediate results

**Features**:
- Step result storage
- Context sharing between services
- Execution history and audit trails

### Message Flow Architecture

#### Pulsar Topics:
- `mapf-plan-requests`
- `mapf-execution-plans` 
- `mapf-step-requests`
- `mapf-step-responses`
- `mapf-completion-notices`

#### Message Schemas:

```python
@dataclasses.dataclass
class StepRequest:
    step_id: str
    plan_id: str
    function_type: str
    parameters: dict
    context: dict
    timeout: int = 300

@dataclasses.dataclass  
class StepResponse:
    step_id: str
    plan_id: str
    success: bool
    result: Any
    confidence: float
    execution_time: float
    error: Optional[str] = None
```

### Integration with Existing Infrastructure

#### Shared Components:
- **Pulsar Messaging**: Reuse existing pub/sub infrastructure
- **Graph RAG**: Query service leverages existing knowledge graph
- **Prompt Templates**: Planning service uses existing template system
- **Configuration**: Extend existing config management

#### Service Registration:
```python
# In service.py for each MAPF service
class MapfPlanningService(BaseService):
    def __init__(self):
        super().__init__()
        self.register_specification(
            PlanRequestSpec(
                request_name="mapf-plan-request",
                response_name="mapf-execution-plan"
            )
        )
```

### Configuration Schema

```yaml
mapf:
  planning:
    model: "gpt-4"
    default_confidence_threshold: 0.7
    max_plan_complexity: 20
  
  execution:
    max_concurrent_steps: 5
    step_timeout: 300
    retry_backoff: exponential
  
  functions:
    query:
      collections: ["default", "research", "technical"]
    external:
      rate_limit: 10 # requests per minute
      timeout: 30
```

### Deployment Considerations

#### Docker Services:
- Each function service as separate container
- Shared base image with common utilities
- Horizontal scaling based on load

#### Development Workflow:
1. Add new function services in `trustgraph-mapf-functions/`
2. Implement service interface and Pulsar specs
3. Add to docker-compose and deployment scripts
4. Create integration tests

### Comparison with ReAct

| Aspect | ReAct | MAPF |
|--------|-------|------|
| Planning | Iterative, step-by-step | Upfront, complete plan |
| Execution | Sequential reasoning cycles | Parallel, dependency-based |
| Error Handling | Human-readable error messages | Confidence-based retries |
| Use Cases | Interactive problem solving | Batch processing, complex workflows |
| LLM Usage | High (every iteration) | Medium (planning phase) |

### Implementation Phases

#### Phase 1: Core Infrastructure
- Planning service with basic plan generation
- Flow controller with sequential execution
- Query service integration
- Basic Pulsar messaging

#### Phase 2: Function Services
- Implement processing services (compare, evaluate, etc.)
- External query service with web search
- Document service for output generation
- Confidence scoring mechanisms

#### Phase 3: Advanced Features
- Parallel execution optimization
- Dynamic plan modification
- Performance monitoring and analytics
- Integration with existing agent tools

### Success Metrics

- **Plan Success Rate**: % of plans that complete successfully
- **Confidence Accuracy**: How well confidence scores predict success
- **Execution Time**: Average time from request to completion
- **Resource Utilization**: Service load balancing and efficiency
- **Error Recovery**: Success rate of retry mechanisms

### Example Plan Generation

For a request like "Compare the top 3 machine learning frameworks and recommend the best for a startup":

```json
{
  "plan_id": "plan-12345",
  "confidence_threshold": 0.7,
  "max_retries": 3,
  "steps": [
    {
      "step_id": "step-1",
      "function_type": "query",
      "parameters": {
        "question": "What are the top machine learning frameworks?",
        "collection": "technical"
      },
      "confidence_threshold": 0.8,
      "dependencies": []
    },
    {
      "step_id": "step-2",
      "function_type": "external_query",
      "parameters": {
        "query": "latest ML framework popularity statistics 2024",
        "sources": ["web", "github"]
      },
      "confidence_threshold": 0.6,
      "dependencies": []
    },
    {
      "step_id": "step-3",
      "function_type": "filter",
      "parameters": {
        "input": "${step-1.result}",
        "criteria": "top_3_by_popularity",
        "additional_data": "${step-2.result}"
      },
      "confidence_threshold": 0.7,
      "dependencies": ["step-1", "step-2"]
    },
    {
      "step_id": "step-4",
      "function_type": "compare",
      "parameters": {
        "items": "${step-3.result}",
        "criteria": ["ease_of_use", "community_support", "performance", "cost"]
      },
      "confidence_threshold": 0.7,
      "dependencies": ["step-3"]
    },
    {
      "step_id": "step-5",
      "function_type": "evaluate",
      "parameters": {
        "comparison": "${step-4.result}",
        "context": "startup with limited resources"
      },
      "confidence_threshold": 0.75,
      "dependencies": ["step-4"]
    },
    {
      "step_id": "step-6",
      "function_type": "document",
      "parameters": {
        "type": "recommendation_report",
        "evaluation": "${step-5.result}",
        "comparison": "${step-4.result}",
        "format": "markdown"
      },
      "confidence_threshold": 0.8,
      "dependencies": ["step-5"]
    }
  ]
}
```

### API Endpoints

The framework will expose the following REST API endpoints through the gateway:

- `POST /mapf/plan` - Submit a new planning request
- `GET /mapf/plan/{plan_id}` - Get plan status and details
- `GET /mapf/plan/{plan_id}/steps/{step_id}` - Get specific step results
- `POST /mapf/plan/{plan_id}/retry` - Retry a failed plan
- `DELETE /mapf/plan/{plan_id}` - Cancel an executing plan

### Testing Strategy

#### Unit Tests:
- Planning service plan generation
- Individual function service logic
- Confidence scoring algorithms
- Message serialization/deserialization

#### Integration Tests:
- End-to-end plan execution
- Service communication via Pulsar
- Error handling and retry logic
- Context persistence

#### Performance Tests:
- Plan execution throughput
- Service scaling behavior
- Message queue performance
- Resource utilization

This framework provides a complementary approach to the ReAct system, offering structured planning and execution for complex, multi-step tasks while leveraging the existing TrustGraph infrastructure.