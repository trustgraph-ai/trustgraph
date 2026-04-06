The Ollama service URL must be provided in a Kubernetes secret.

```bash
kubectl -n {{namespace}} \
    create secret generic ollama-credentials \
    --from-literal=ollama-host=http://ollama:11434/
```

Replace the URL with the URL of your Ollama service.
