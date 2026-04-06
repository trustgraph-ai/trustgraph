To use Azure's OpenAI APIs, you need to have a serverless OpenAI endpoint deployed. You must also provide an endpoint token, API version, and model name in a Kubernetes secret. The Model Name is set by the user during the deployment within AzureAI.

```bash
kubectl -n {{namespace}} create secret \
    generic azure-openai-credentials \
    --from-literal=azure-endpoint=https://ENDPOINT.API.HOST.GOES.HERE/ \
    --from-literal=azure-token=TOKEN-GOES-HERE \
    --from-literal=azure-api-version=API-VERSION-GOES-HERE \
    --from-literal=azure-model=MODEL-NAME-GOES-HERE
```
