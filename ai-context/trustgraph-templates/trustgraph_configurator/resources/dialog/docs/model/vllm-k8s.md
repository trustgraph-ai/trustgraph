The vLLM service URL must be provided in a Kubernetes secret.

```bash
kubectl -n {{namespace}} \
    create secret generic vllm-credentials \
    --from-literal=vllm-url=http://vllm:8000/v1
```

Replace the URL with the URL of your vLLM service.
