# TrustGraph Metrics API

This API provides access to TrustGraph system metrics through a Prometheus proxy endpoint. 
It allows authenticated access to monitoring and observability data from the TrustGraph 
system components.

## Overview

The Metrics API is implemented as a proxy to a Prometheus metrics server, providing:
- System performance metrics
- Service health information  
- Resource utilization data
- Request/response statistics
- Error rates and latency metrics

## Authentication

All metrics endpoints require Bearer token authentication:

```
Authorization: Bearer <your-api-token>
```

Unauthorized requests return HTTP 401.

## Endpoint

**Base Path:** `/api/metrics`

**Method:** GET

**Description:** Proxies requests to the underlying Prometheus API

## Usage Examples

### Query Current Metrics

```bash
# Get all available metrics
curl -H "Authorization: Bearer your-token" \
  "http://api-gateway:8080/api/metrics/query?query=up"

# Get specific metric with time range
curl -H "Authorization: Bearer your-token" \
  "http://api-gateway:8080/api/metrics/query_range?query=cpu_usage&start=1640995200&end=1640998800&step=60"

# Get metric metadata
curl -H "Authorization: Bearer your-token" \
  "http://api-gateway:8080/api/metrics/metadata"
```

### Common Prometheus API Endpoints

The metrics API supports all standard Prometheus API endpoints:

#### Instant Queries
```
GET /api/metrics/query?query=<prometheus_query>
```

#### Range Queries  
```
GET /api/metrics/query_range?query=<query>&start=<timestamp>&end=<timestamp>&step=<duration>
```

#### Metadata
```
GET /api/metrics/metadata
GET /api/metrics/metadata?metric=<metric_name>
```

#### Series
```
GET /api/metrics/series?match[]=<series_selector>
```

#### Label Values
```
GET /api/metrics/label/<label_name>/values
```

#### Targets
```
GET /api/metrics/targets
```

## Example Queries

### System Health
```bash
# Check if services are up
curl -H "Authorization: Bearer token" \
  "http://api-gateway:8080/api/metrics/query?query=up"

# Get service uptime
curl -H "Authorization: Bearer token" \
  "http://api-gateway:8080/api/metrics/query?query=time()-process_start_time_seconds"
```

### Performance Metrics
```bash
# CPU usage
curl -H "Authorization: Bearer token" \
  "http://api-gateway:8080/api/metrics/query?query=rate(cpu_seconds_total[5m])"

# Memory usage
curl -H "Authorization: Bearer token" \
  "http://api-gateway:8080/api/metrics/query?query=process_resident_memory_bytes"

# Request rate
curl -H "Authorization: Bearer token" \
  "http://api-gateway:8080/api/metrics/query?query=rate(http_requests_total[5m])"
```

### TrustGraph-Specific Metrics
```bash
# Document processing rate
curl -H "Authorization: Bearer token" \
  "http://api-gateway:8080/api/metrics/query?query=rate(trustgraph_documents_processed_total[5m])"

# Knowledge graph size
curl -H "Authorization: Bearer token" \
  "http://api-gateway:8080/api/metrics/query?query=trustgraph_triples_count"

# Embedding generation rate
curl -H "Authorization: Bearer token" \
  "http://api-gateway:8080/api/metrics/query?query=rate(trustgraph_embeddings_generated_total[5m])"
```

## Response Format

Responses follow the standard Prometheus API format:

### Successful Query Response
```json
{
    "status": "success",
    "data": {
        "resultType": "vector",
        "result": [
            {
                "metric": {
                    "__name__": "up",
                    "instance": "api-gateway:8080",
                    "job": "trustgraph"
                },
                "value": [1640995200, "1"]
            }
        ]
    }
}
```

### Range Query Response
```json
{
    "status": "success", 
    "data": {
        "resultType": "matrix",
        "result": [
            {
                "metric": {
                    "__name__": "cpu_usage",
                    "instance": "worker-1"
                },
                "values": [
                    [1640995200, "0.15"],
                    [1640995260, "0.18"],
                    [1640995320, "0.12"]
                ]
            }
        ]
    }
}
```

### Error Response
```json
{
    "status": "error",
    "errorType": "bad_data",
    "error": "invalid query syntax"
}
```

## Available Metrics

### Standard System Metrics
- `up`: Service availability (1 = up, 0 = down)
- `process_resident_memory_bytes`: Memory usage
- `process_cpu_seconds_total`: CPU time
- `http_requests_total`: HTTP request count
- `http_request_duration_seconds`: Request latency

### TrustGraph-Specific Metrics
- `trustgraph_documents_processed_total`: Documents processed count
- `trustgraph_triples_count`: Knowledge graph triple count
- `trustgraph_embeddings_generated_total`: Embeddings generated count
- `trustgraph_flow_executions_total`: Flow execution count
- `trustgraph_pulsar_messages_total`: Pulsar message count
- `trustgraph_errors_total`: Error count by component

## Time Series Queries

### Time Ranges
Use standard Prometheus time range formats:
- `5m`: 5 minutes
- `1h`: 1 hour  
- `1d`: 1 day
- `1w`: 1 week

### Rate Calculations
```bash
# 5-minute rate
rate(metric_name[5m])

# Increase over time
increase(metric_name[1h])
```

### Aggregations
```bash
# Sum across instances
sum(metric_name)

# Average by label
avg by (instance) (metric_name)

# Top 5 values
topk(5, metric_name)
```

## Integration Examples

### Python Integration
```python
import requests

def query_metrics(token, query):
    headers = {"Authorization": f"Bearer {token}"}
    params = {"query": query}
    
    response = requests.get(
        "http://api-gateway:8080/api/metrics/query",
        headers=headers,
        params=params
    )
    
    return response.json()

# Get system uptime
uptime = query_metrics("your-token", "time() - process_start_time_seconds")
```

### JavaScript Integration
```javascript
async function queryMetrics(token, query) {
    const response = await fetch(
        `http://api-gateway:8080/api/metrics/query?query=${encodeURIComponent(query)}`,
        {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        }
    );
    
    return await response.json();
}

// Get request rate
const requestRate = await queryMetrics('your-token', 'rate(http_requests_total[5m])');
```

## Error Handling

### Common HTTP Status Codes
- `200`: Success
- `400`: Bad request (invalid query)
- `401`: Unauthorized (invalid/missing token)
- `422`: Unprocessable entity (query execution error)
- `500`: Internal server error

### Error Types
- `bad_data`: Invalid query syntax
- `timeout`: Query execution timeout
- `canceled`: Query was canceled
- `execution`: Query execution error

## Best Practices

### Query Optimization
- Use appropriate time ranges to limit data volume
- Apply label filters to reduce result sets
- Use recording rules for frequently accessed metrics

### Rate Limiting
- Avoid high-frequency polling
- Cache results when appropriate
- Use appropriate step sizes for range queries

### Security
- Keep API tokens secure
- Use HTTPS in production
- Rotate tokens regularly

## Use Cases

- **System Monitoring**: Track system health and performance
- **Capacity Planning**: Monitor resource utilization trends  
- **Alerting**: Set up alerts based on metric thresholds
- **Performance Analysis**: Analyze system performance over time
- **Debugging**: Investigate issues using detailed metrics
- **Business Intelligence**: Track document processing and knowledge extraction metrics