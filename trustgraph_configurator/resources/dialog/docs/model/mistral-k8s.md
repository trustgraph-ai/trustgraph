To use Mistral, you need a Mistral API key which must be provided in a Kubernetes secret.

```bash
kubectl -n {{namespace}} create secret \
    generic mistral-credentials \
    --from-literal=mistral-key=MISTRAL-TOKEN
```
