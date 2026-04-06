To use Google AI Studio APIs, you need an API token which must be provided in a Kubernetes secret.

```bash
kubectl -n {{namespace}} create secret \
    generic googleaistudio-credentials \
    --from-literal=google-ai-studio-key=GOOGLEAISTUDIO-KEY
```
