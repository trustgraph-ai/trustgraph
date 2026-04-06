Text Generation Inference (TGI) is Hugging Face's production-ready inference server for LLMs. It provides high-performance text generation with features like continuous batching, tensor parallelism, and optimized attention mechanisms.

The TGI service must be running with the required model loaded. The TGI service URL must be provided in an environment variable.

```
TGI_BASE_URL=http://tgi-host:8080/v1
```

Replace the URL with the URL of your TGI service, noting the `v1` suffix for OpenAI-compatible API.
