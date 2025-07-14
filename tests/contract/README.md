# Contract Tests for TrustGraph

This directory contains contract tests that verify service interface contracts, message schemas, and API compatibility across the TrustGraph microservices architecture.

## Overview

Contract tests ensure that:
- **Message schemas remain compatible** across service versions
- **API interfaces stay stable** for consumers
- **Service communication contracts** are maintained
- **Schema evolution** doesn't break existing integrations

## Test Categories

### 1. Pulsar Message Schema Contracts (`test_message_contracts.py`)

Tests the contracts for all Pulsar message schemas used in TrustGraph service communication.

#### **Coverage:**
- ✅ **Text Completion Messages**: `TextCompletionRequest` ↔ `TextCompletionResponse`
- ✅ **Document RAG Messages**: `DocumentRagQuery` ↔ `DocumentRagResponse`
- ✅ **Agent Messages**: `AgentRequest` ↔ `AgentResponse` ↔ `AgentStep`
- ✅ **Graph Messages**: `Chunk` → `Triple` → `Triples` → `EntityContext`
- ✅ **Common Messages**: `Metadata`, `Value`, `Error` schemas
- ✅ **Message Routing**: Properties, correlation IDs, routing keys
- ✅ **Schema Evolution**: Backward/forward compatibility testing
- ✅ **Serialization**: Schema validation and data integrity

#### **Key Features:**
- **Schema Validation**: Ensures all message schemas accept valid data and reject invalid data
- **Field Contracts**: Validates required vs optional fields and type constraints
- **Nested Schema Support**: Tests complex schemas with embedded objects and arrays
- **Routing Contracts**: Validates message properties and routing conventions
- **Evolution Testing**: Backward compatibility and schema versioning support

## Running Contract Tests

### Run All Contract Tests
```bash
pytest tests/contract/ -m contract
```

### Run Specific Contract Test Categories
```bash
# Message schema contracts
pytest tests/contract/test_message_contracts.py -v

# Specific test class
pytest tests/contract/test_message_contracts.py::TestTextCompletionMessageContracts -v

# Schema evolution tests
pytest tests/contract/test_message_contracts.py::TestSchemaEvolutionContracts -v
```

### Run with Coverage
```bash
pytest tests/contract/ -m contract --cov=trustgraph.schema --cov-report=html
```

## Contract Test Patterns

### 1. Schema Validation Pattern
```python
@pytest.mark.contract
def test_schema_contract(self, sample_message_data):
    """Test that schema accepts valid data and rejects invalid data"""
    # Arrange
    valid_data = sample_message_data["SchemaName"]
    
    # Act & Assert
    assert validate_schema_contract(SchemaClass, valid_data)
    
    # Test field constraints
    instance = SchemaClass(**valid_data)
    assert hasattr(instance, 'required_field')
    assert isinstance(instance.required_field, expected_type)
```

### 2. Serialization Contract Pattern
```python
@pytest.mark.contract  
def test_serialization_contract(self, sample_message_data):
    """Test schema serialization/deserialization contracts"""
    # Arrange
    data = sample_message_data["SchemaName"]
    
    # Act & Assert
    assert serialize_deserialize_test(SchemaClass, data)
```

### 3. Evolution Contract Pattern
```python
@pytest.mark.contract
def test_backward_compatibility_contract(self, schema_evolution_data):
    """Test that new schema versions accept old data formats"""
    # Arrange
    old_version_data = schema_evolution_data["SchemaName_v1"]
    
    # Act - Should work with current schema
    instance = CurrentSchema(**old_version_data)
    
    # Assert - Required fields maintained
    assert instance.required_field == expected_value
```

## Schema Registry

The contract tests maintain a registry of all TrustGraph schemas:

```python
schema_registry = {
    # Text Completion
    "TextCompletionRequest": TextCompletionRequest,
    "TextCompletionResponse": TextCompletionResponse,
    
    # Document RAG  
    "DocumentRagQuery": DocumentRagQuery,
    "DocumentRagResponse": DocumentRagResponse,
    
    # Agent
    "AgentRequest": AgentRequest,
    "AgentResponse": AgentResponse,
    
    # Graph/Knowledge
    "Chunk": Chunk,
    "Triple": Triple,
    "Triples": Triples,
    "Value": Value,
    
    # Common
    "Metadata": Metadata,
    "Error": Error,
}
```

## Message Contract Specifications

### Text Completion Service Contract
```yaml
TextCompletionRequest:
  required_fields: [system, prompt]
  field_types:
    system: string
    prompt: string

TextCompletionResponse:
  required_fields: [error, response, model]  
  field_types:
    error: Error | null
    response: string | null
    in_token: integer | null
    out_token: integer | null
    model: string
```

### Document RAG Service Contract
```yaml
DocumentRagQuery:
  required_fields: [query, user, collection]
  field_types:
    query: string
    user: string
    collection: string
    doc_limit: integer

DocumentRagResponse:
  required_fields: [error, response]
  field_types:
    error: Error | null
    response: string | null
```

### Agent Service Contract
```yaml
AgentRequest:
  required_fields: [question, history]
  field_types:
    question: string
    plan: string
    state: string
    history: Array<AgentStep>

AgentResponse:
  required_fields: [error]
  field_types:
    answer: string | null
    error: Error | null
    thought: string | null
    observation: string | null
```

## Best Practices

### Contract Test Design
1. **Test Both Valid and Invalid Data**: Ensure schemas accept valid data and reject invalid data
2. **Verify Field Constraints**: Test type constraints, required vs optional fields
3. **Test Nested Schemas**: Validate complex objects with embedded schemas
4. **Test Array Fields**: Ensure array serialization maintains order and content
5. **Test Optional Fields**: Verify optional field handling in serialization

### Schema Evolution
1. **Backward Compatibility**: New schema versions must accept old message formats
2. **Required Field Stability**: Required fields should never become optional or be removed
3. **Additive Changes**: New fields should be optional to maintain compatibility
4. **Deprecation Strategy**: Plan deprecation path for schema changes

### Error Handling
1. **Error Schema Consistency**: All error responses use consistent Error schema
2. **Error Type Contracts**: Error types follow naming conventions
3. **Error Message Format**: Error messages provide actionable information

## Adding New Contract Tests

When adding new message schemas or modifying existing ones:

1. **Add to Schema Registry**: Update `conftest.py` schema registry
2. **Add Sample Data**: Create valid sample data in `conftest.py`
3. **Create Contract Tests**: Follow existing patterns for validation
4. **Test Evolution**: Add backward compatibility tests
5. **Update Documentation**: Document schema contracts in this README

## Integration with CI/CD

Contract tests should be run:
- **On every commit** to detect breaking changes early
- **Before releases** to ensure API stability
- **On schema changes** to validate compatibility
- **In dependency updates** to catch breaking changes

```bash
# CI/CD pipeline command
pytest tests/contract/ -m contract --junitxml=contract-test-results.xml
```

## Contract Test Results

Contract tests provide:
- ✅ **Schema Compatibility Reports**: Which schemas pass/fail validation
- ✅ **Breaking Change Detection**: Identifies contract violations
- ✅ **Evolution Validation**: Confirms backward compatibility
- ✅ **Field Constraint Verification**: Validates data type contracts

This ensures that TrustGraph services can evolve independently while maintaining stable, compatible interfaces for all service communication.