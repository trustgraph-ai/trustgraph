# Structured Data Diagnostic Service Technical Specification

## Overview

This specification describes a new invokable service for diagnosing and analyzing structured data within TrustGraph. The service extracts functionality from the existing `tg-load-structured-data` command-line tool and exposes it as a request/response service, enabling programmatic access to data type detection and descriptor generation capabilities.

The service supports three primary operations:

1. **Data Type Detection**: Analyze a data sample to determine its format (CSV, JSON, or XML)
2. **Descriptor Generation**: Generate a TrustGraph structured data descriptor for a given data sample and type
3. **Combined Diagnosis**: Perform both type detection and descriptor generation in sequence

## Goals

- **Modularize Data Analysis**: Extract data diagnosis logic from CLI into reusable service components
- **Enable Programmatic Access**: Provide API-based access to data analysis capabilities
- **Support Multiple Data Formats**: Handle CSV, JSON, and XML data formats consistently
- **Generate Accurate Descriptors**: Produce structured data descriptors that accurately map source data to TrustGraph schemas
- **Maintain Backward Compatibility**: Ensure existing CLI functionality continues to work
- **Enable Service Composition**: Allow other services to leverage data diagnosis capabilities
- **Improve Testability**: Separate business logic from CLI interface for better testing
- **Support Streaming Analysis**: Enable analysis of data samples without loading entire files

## Background

Currently, the `tg-load-structured-data` command provides comprehensive functionality for analyzing structured data and generating descriptors. However, this functionality is tightly coupled to the CLI interface, limiting its reusability.

Current limitations include:
- Data diagnosis logic embedded in CLI code
- No programmatic access to type detection and descriptor generation
- Difficult to integrate diagnosis capabilities into other services
- Limited ability to compose data analysis workflows

This specification addresses these gaps by creating a dedicated service for structured data diagnosis. By exposing these capabilities as a service, TrustGraph can:
- Enable other services to analyze data programmatically
- Support more complex data processing pipelines
- Facilitate integration with external systems
- Improve maintainability through separation of concerns

## Technical Design

### Architecture

The structured data diagnostic service requires the following technical components:

1. **Diagnostic Service Processor**
   - Handles incoming diagnosis requests
   - Orchestrates type detection and descriptor generation
   - Returns structured responses with diagnosis results

   Module: `trustgraph-flow/trustgraph/diagnosis/structured_data/service.py`

2. **Data Type Detector**
   - Uses algorithmic detection to identify data format (CSV, JSON, XML)
   - Analyzes data structure, delimiters, and syntax patterns
   - Returns detected format and confidence scores

   Module: `trustgraph-flow/trustgraph/diagnosis/structured_data/type_detector.py`

3. **Descriptor Generator**
   - Uses prompt service to generate descriptors
   - Invokes format-specific prompts (diagnose-csv, diagnose-json, diagnose-xml)
   - Maps data fields to TrustGraph schema fields through prompt responses

   Module: `trustgraph-flow/trustgraph/diagnosis/structured_data/descriptor_generator.py`

### Data Models

#### StructuredDataDiagnosisRequest

Request message for structured data diagnosis operations:

```python
class StructuredDataDiagnosisRequest:
    operation: str  # "detect-type", "generate-descriptor", or "diagnose"
    sample: str     # Data sample to analyze (text content)
    type: Optional[str]  # Data type (csv, json, xml) - required for generate-descriptor
    schema_name: Optional[str]  # Target schema name for descriptor generation
    options: Dict[str, Any]  # Additional options (e.g., delimiter for CSV)
```

#### StructuredDataDiagnosisResponse

Response message containing diagnosis results:

```python
class StructuredDataDiagnosisResponse:
    operation: str  # The operation that was performed
    detected_type: Optional[str]  # Detected data type (for detect-type/diagnose)
    confidence: Optional[float]  # Confidence score for type detection
    descriptor: Optional[Dict]  # Generated descriptor (for generate-descriptor/diagnose)
    error: Optional[str]  # Error message if operation failed
    metadata: Dict[str, Any]  # Additional metadata (e.g., field count, sample records)
```

#### Descriptor Structure

The generated descriptor follows the existing structured data descriptor format:

```json
{
  "format": {
    "type": "csv",
    "encoding": "utf-8",
    "options": {
      "delimiter": ",",
      "has_header": true
    }
  },
  "mappings": [
    {
      "source_field": "customer_id",
      "target_field": "id",
      "transforms": [
        {"type": "trim"}
      ]
    }
  ],
  "output": {
    "schema_name": "customer",
    "options": {
      "batch_size": 1000,
      "confidence": 0.9
    }
  }
}
```

### Service Interface

The service will expose the following operations through the request/response pattern:

1. **Type Detection Operation**
   - Input: Data sample
   - Processing: Analyze data structure using algorithmic detection
   - Output: Detected type with confidence score

2. **Descriptor Generation Operation**
   - Input: Data sample, type, target schema name
   - Processing:
     - Call prompt service with format-specific prompt ID (diagnose-csv, diagnose-json, or diagnose-xml)
     - Pass data sample and available schemas to prompt
     - Receive generated descriptor from prompt response
   - Output: Structured data descriptor

3. **Combined Diagnosis Operation**
   - Input: Data sample, optional schema name
   - Processing:
     - Use algorithmic detection to identify format first
     - Select appropriate format-specific prompt based on detected type
     - Call prompt service to generate descriptor
   - Output: Both detected type and descriptor

### Implementation Details

The service will follow TrustGraph service conventions:

1. **Service Registration**
   - Register as `structured-diag` service type
   - Use standard request/response topics
   - Implement FlowProcessor base class
   - Register PromptClientSpec for prompt service interaction

2. **Configuration Management**
   - Access schema configurations via config service
   - Cache schemas for performance
   - Handle configuration updates dynamically

3. **Prompt Integration**
   - Use existing prompt service infrastructure
   - Call prompt service with format-specific prompt IDs:
     - `diagnose-csv`: For CSV data analysis
     - `diagnose-json`: For JSON data analysis
     - `diagnose-xml`: For XML data analysis
   - Prompts are configured in prompt config, not hard-coded in service
   - Pass schemas and data samples as prompt variables
   - Parse prompt responses to extract descriptors

4. **Error Handling**
   - Validate input data samples
   - Provide descriptive error messages
   - Handle malformed data gracefully
   - Handle prompt service failures

5. **Data Sampling**
   - Process configurable sample sizes
   - Handle incomplete records appropriately
   - Maintain sampling consistency

### API Integration

The service will integrate with existing TrustGraph APIs:

Modified Components:
- `tg-load-structured-data` CLI - Refactored to use the new service for diagnosis operations
- Flow API - Extended to support structured data diagnosis requests

New Service Endpoints:
- `/api/v1/flow/{flow}/diagnose/structured-data` - WebSocket endpoint for diagnosis requests
- `/api/v1/diagnose/structured-data` - REST endpoint for synchronous diagnosis

### Message Flow

```
Client → Gateway → Structured Diag Service → Config Service (for schemas)
                                           ↓
                                    Type Detector (algorithmic)
                                           ↓
                                    Prompt Service (diagnose-csv/json/xml)
                                           ↓
                                 Descriptor Generator (parses prompt response)
                                           ↓
Client ← Gateway ← Structured Diag Service (response)
```

## Security Considerations

- Input validation to prevent injection attacks
- Size limits on data samples to prevent DoS
- Sanitization of generated descriptors
- Access control through existing TrustGraph authentication

## Performance Considerations

- Cache schema definitions to reduce config service calls
- Limit sample sizes to maintain responsive performance
- Use streaming processing for large data samples
- Implement timeout mechanisms for long-running analyses

## Testing Strategy

1. **Unit Tests**
   - Type detection for various data formats
   - Descriptor generation accuracy
   - Error handling scenarios

2. **Integration Tests**
   - Service request/response flow
   - Schema retrieval and caching
   - CLI integration

3. **Performance Tests**
   - Large sample processing
   - Concurrent request handling
   - Memory usage under load

## Migration Plan

1. **Phase 1**: Implement service with core functionality
2. **Phase 2**: Refactor CLI to use service (maintain backward compatibility)
3. **Phase 3**: Add REST API endpoints
4. **Phase 4**: Deprecate embedded CLI logic (with notice period)

## Timeline

- Week 1-2: Implement core service and type detection
- Week 3-4: Add descriptor generation and integration
- Week 5: Testing and documentation
- Week 6: CLI refactoring and migration

## Open Questions

- Should the service support additional data formats (e.g., Parquet, Avro)?
- What should be the maximum sample size for analysis?
- Should diagnosis results be cached for repeated requests?
- How should the service handle multi-schema scenarios?
- Should the prompt IDs be configurable parameters for the service?

## References

- [Structured Data Descriptor Specification](structured-data-descriptor.md)
- [Structured Data Loading Documentation](structured-data.md)
- `tg-load-structured-data` implementation: `trustgraph-cli/trustgraph/cli/load_structured_data.py`