To use Azure Serverless APIs, you need to have a serverless endpoint deployed. You must also provide an Azure endpoint and token in a Kubernetes secret before launching the application.

```bash
kubectl -n {{namespace}} create secret \
    generic azure-credentials \
    --from-literal=azure-endpoint=AZURE-ENDPOINT \
    --from-literal=azure-token=AZURE-TOKEN
```
