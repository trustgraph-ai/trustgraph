The power of Ollama is the flexibility it provides in Language Model deployments. Being able to run LMs with Ollama enables fully secure AI TrustGraph pipelines that aren't relying on any external APIs. No data is leaving the host environment or network.

The Ollama service must be running, and have required models available using `ollama pull`. The Ollama service URL must be provided in an environment variable.

```
OLLAMA_HOST=http://ollama-host:11434
```

Replace the URL with the URL of your Ollama service.
