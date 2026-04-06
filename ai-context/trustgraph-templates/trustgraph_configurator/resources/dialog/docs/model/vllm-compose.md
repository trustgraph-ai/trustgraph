vLLM is a high-throughput, memory-efficient inference and serving engine for LLMs. Using PagedAttention and continuous batching, vLLM enables fully secure AI TrustGraph pipelines that aren't relying on any external APIs. No data is leaving the host environment or network.

The vLLM service must be running with the required model loaded using `vllm serve`. The vLLM service URL must be provided in an environment variable.

```
VLLM_BASE_URL=http://vllm-host:8000/v1
```

Replace the URL with the URL of your vLLM service, noting the `v1` suffix.
