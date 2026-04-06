To use Pinecone, you need an API token which must be provided in a Kubernetes secret.

```bash
kubectl -n {{namespace}} create secret \
    generic pinecone-api-key \
    --from-literal=pinecone-api-key=PINECONE-API-KEY
```
