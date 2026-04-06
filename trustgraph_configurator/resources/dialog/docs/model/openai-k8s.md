To use OpenAI APIs, you need an API token which must be provided in a Kubernetes secret.

```bash
kubectl -n {{namespace}} create secret \
    generic openai-credentials \
    --from-literal=openai-token=OPENAI-TOKEN-HERE
```
