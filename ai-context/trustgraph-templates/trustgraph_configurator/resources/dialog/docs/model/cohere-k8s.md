To use Cohere APIs, you need an API token which must be provided in a Kubernetes secret.

```bash
kubectl -n {{namespace}} create secret \
    generic cohere-credentials \
    --from-literal=cohere-key=COHERE-KEY
```
